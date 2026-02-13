# Terminal Broker Architecture

> **Purpose**: Prevent Daphne server deadlocks by isolating PTY operations from the asyncio event loop.

## Problem Statement

### The Incident (2025-02-01)

The production server (scitex.ai) experienced complete unresponsiveness:
- All 36 Daphne worker threads blocked on `futex_wait` (kernel mutex)
- Health checks failed for 25+ consecutive attempts
- Zombie processes `[srun] <defunct>` accumulated
- Server required restart to recover

### Root Cause

Running `pty.fork()` inside Daphne's asyncio event loop causes deadlocks:

```
TerminalConsumer.connect()
    → pty.fork()                    # Creates child process
    → pthread_sigmask()             # Blocks signals during fork
    → SIGCHLD arrives               # Child state change
    → asyncio tries to handle       # CONFLICT!
    → futex_wait deadlock           # All threads blocked
```

**Why this happens:**
1. `pty.fork()` uses low-level POSIX signals (SIGCHLD)
2. `pthread_sigmask()` used to block signals during fork
3. asyncio has its own signal handling mechanism
4. These two signal handling approaches conflict
5. Unrepaped children become zombies, further destabilizing

## Solution: Terminal Broker Architecture

### Design Principle

**Isolate all PTY operations in a separate process that has no asyncio.**

```
┌─────────────────────────────────────────────────────────────────┐
│                         DAPHNE (asyncio)                        │
│  ┌──────────────────┐                                           │
│  │ TerminalConsumer │──── Unix Socket ────┐                     │
│  │   (WebSocket)    │      IPC            │                     │
│  └──────────────────┘                     │                     │
└───────────────────────────────────────────│─────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TERMINAL BROKER (no asyncio)                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  /tmp/scitex-terminal-broker.sock                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                    │
│              ┌─────────────┼─────────────┐                      │
│              ▼             ▼             ▼                      │
│         ┌────────┐    ┌────────┐    ┌────────┐                  │
│         │Session1│    │Session2│    │Session3│   pty.fork()     │
│         │ PTY/FD │    │ PTY/FD │    │ PTY/FD │   runs HERE      │
│         └────────┘    └────────┘    └────────┘                  │
│                                                                 │
│         SIGCHLD handler → os.waitpid() → zombie reaping        │
└─────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                              ┌──────────────────────┐
                              │  srun --pty bash     │
                              │  (SLURM + Apptainer) │
                              └──────────────────────┘
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Terminal Broker | `apps/console_app/services/terminal_broker.py` | Standalone process for PTY ops |
| Terminal Client | `apps/console_app/services/terminal_client.py` | Async IPC client for consumers |
| Management Command | `apps/console_app/management/commands/run_terminal_broker.py` | Start broker via Django |
| Consumer | `apps/console_app/views/terminal/consumer.py` | WebSocket handler, uses client |

### Communication Protocol

Length-prefixed JSON over Unix socket:

```
┌──────────────┬─────────────────────────────────┐
│ 4 bytes (BE) │         JSON payload            │
│   length     │                                 │
└──────────────┴─────────────────────────────────┘
```

**Message Types:**

```python
# Spawn request (consumer → broker)
{
    "type": "spawn",
    "username": "alice",
    "user_data_dir": "/data/users/alice",
    "project_dir": "/data/users/alice/proj/myproject",
    "container_path": "/containers/scitex.sif",
    "project_slug": "myproject"
}

# Spawn response (broker → consumer)
{
    "type": "spawned",
    "session_id": "abc123"
}

# Input (consumer → broker)
{
    "type": "input",
    "data": "base64-encoded-bytes"
}

# Output (broker → consumer)
{
    "type": "output",
    "data": "base64-encoded-bytes"
}

# Resize (consumer → broker)
{
    "type": "resize",
    "rows": 24,
    "cols": 80
}
```

## Deployment

### Automatic Startup

The broker starts automatically before Django in entrypoint scripts:

```bash
# deployment/docker/common/scripts/entrypoint-*.sh
start_terminal_broker_if_needed() {
    local socket_path="/tmp/scitex-terminal-broker.sock"
    if [ ! -S "$socket_path" ]; then
        echo_info "Starting terminal broker..."
        nohup python manage.py run_terminal_broker \
            >/app/logs/terminal-broker.log 2>&1 &
    fi
}
start_terminal_broker_if_needed
```

### Manual Control

```bash
# Start broker manually
python manage.py run_terminal_broker

# Check if running
ls -la /tmp/scitex-terminal-broker.sock

# View logs
tail -f /app/logs/terminal-broker.log

# Stop broker (will restart on next container start)
pkill -f "run_terminal_broker"
```

## Fallback Mode

If the broker is unavailable, the consumer falls back to direct `pty.fork()`:

```python
# consumer.py
if await _check_broker():
    self.use_broker = True
    await self._spawn_via_broker()
else:
    logger.warning("Terminal broker unavailable, using direct pty.fork()")
    self.use_broker = False
    await self._spawn_direct()
```

**Warning:** Direct mode is deprecated and may cause deadlocks under load.

## Troubleshooting

### Broker Not Starting

```bash
# Check socket exists
ls -la /tmp/scitex-terminal-broker.sock

# Check process
ps aux | grep terminal_broker

# Check logs
cat /app/logs/terminal-broker.log
```

### Zombie Processes

The broker handles SIGCHLD automatically. If zombies appear:

```bash
# Check for zombies
ps aux | grep defunct

# The broker should reap them automatically
# If not, check broker is running
```

### Terminal Connection Fails

1. Check broker socket exists
2. Check broker process is running
3. Check SLURM is available (`sinfo`)
4. Check container exists at expected path

### Complete Deadlock (All Threads Blocked)

This should NOT happen with broker architecture. If it does:

```bash
# Emergency: Restart container
docker restart scitex-cloud-prod-django-1

# Investigate: Check if broker was bypassed
grep "direct pty.fork" /app/logs/django.log
```

## Monitoring

### Health Indicators

| Metric | Healthy | Unhealthy |
|--------|---------|-----------|
| Broker socket | Exists | Missing |
| Zombie count | 0 | > 0 |
| Daphne threads on futex | Some | All 36 |
| Terminal WebSocket success | > 95% | < 90% |

### Key Log Patterns

```bash
# Good: Using broker
grep "Using terminal broker" /app/logs/django.log

# Bad: Falling back to direct mode
grep "using direct pty.fork" /app/logs/django.log

# Bad: Broker spawn failed
grep "Broker spawn failed" /app/logs/django.log
```

## History

| Date | Event |
|------|-------|
| 2025-02-01 | Production deadlock incident, all 36 Daphne threads blocked |
| 2025-02-01 | Root cause identified: pty.fork() + asyncio signal conflict |
| 2025-02-01 | Terminal Broker architecture implemented (commit 64b859fc) |

## References

- [Python pty module](https://docs.python.org/3/library/pty.html)
- [asyncio and signals](https://docs.python.org/3/library/asyncio-eventloop.html#unix-signals)
- [SIGCHLD handling](https://man7.org/linux/man-pages/man7/signal.7.html)
- Related: `docs/TERMINAL_SLURM_SECURITY.md` - SLURM/Apptainer security model
