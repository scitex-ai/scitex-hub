# NAS Stability Guide

## Problem Description

The Synology NAS hosting scitex.ai becomes unreachable under heavy Docker
workload. The Linux OOM killer terminates `sshd`, which prevents remote
recovery. Physical access or WoL + serial console is then the only way back in.

Symptoms observed:

- `curl https://scitex.ai` times out
- `ssh nas` connection refused or hangs
- After reboot, `dmesg` shows OOM kills targeting sshd

## Root Cause Investigation

Run these on the NAS after recovery (or via `diagnose.sh`):

```bash
# Check OOM kill events
dmesg | grep -i "oom\|killed process"

# Check systemd journal for crashes
journalctl -b -1 --priority=err   # previous boot errors
journalctl --since "1 hour ago"

# Docker resource usage
docker stats --no-stream

# Disk pressure
df -h
```

## Permanent Fixes

### 1. Protect sshd from OOM Killer (Critical)

The single most important fix. Ensures SSH access survives memory pressure.

```bash
# Run on NAS:
./protect-sshd.sh
```

This creates a systemd override setting `OOMScoreAdjust=-1000` for sshd,
making it the last process the OOM killer would ever target.

### 2. Docker Memory Limits

Prevent any single container from consuming all system RAM.

```bash
# Run on NAS:
./docker-memory-limits.sh
```

Reviews docker-compose files and applies `mem_limit` constraints.

### 3. Health Check Watchdog

Automated monitoring from WSL that detects failures and self-heals.

```bash
# Installed via install.sh, runs every 5 minutes from cron
./health-check.sh
```

## Recovery Procedure

When the NAS is unreachable:

```bash
# Step 1: Re-establish network route to NAS
nw-nas

# Step 2: Wait ~30 seconds for network to stabilize
sleep 30

# Step 3: Try SSH
ssh nas

# Step 4: If SSH works, check what happened
ssh nas 'dmesg | tail -50'

# Step 5: If SSH fails, the NAS may need a physical power cycle
#         or WoL packet (if configured)
```

## Monitoring Setup

The `health-check.sh` script is designed to run as a cron job on WSL:

```
*/5 * * * * /home/ywatanabe/proj/scitex-cloud/deployment/nas-stability/health-check.sh >> /tmp/nas-health-check.log 2>&1
```

Install automatically with:

```bash
./install.sh
```

## Escalation Flow

The system follows a tiered escalation:

```
Service down detected (curl fails)
    |
    v
[Tier 1] Auto-fix: SSH to NAS, restart Docker containers
    |  (success -> log + done)
    v  (failure)
[Tier 2] Telegram notification to admin
    |
    v  (still down after next check)
[Tier 3] Phone call + SMS via scitex notification system
```

Each tier is handled automatically by `health-check.sh`. No manual
intervention is needed unless Tier 3 fires, which means SSH itself is broken
and the NAS likely needs a physical restart.

## File Inventory

| File                      | Purpose                                    | Runs on |
|---------------------------|--------------------------------------------|---------|
| `protect-sshd.sh`        | OOM-proof sshd                             | NAS     |
| `docker-memory-limits.sh` | Apply container memory caps                | NAS     |
| `health-check.sh`        | Watchdog + auto-recovery + escalation      | WSL     |
| `diagnose.sh`            | Post-incident forensics                    | NAS     |
| `install.sh`             | Master installer for all of the above      | WSL     |
