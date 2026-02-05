# Terminal Security: SLURM-Only Mode

**Date:** 2025-12-05
**Status:** ✅ ENFORCED

## Summary

All interactive terminals now **REQUIRE** SLURM for execution. Direct Apptainer fallbacks have been removed for security and resource management in multi-user environments.

## Changes Made

### 1. Removed Dangerous Fallbacks (`execution.py`)

**Deleted functions:**
- `exec_direct_shell()` - Direct Apptainer execution (DANGEROUS)
- `exec_plain_bash()` - Plain bash fallback (DANGEROUS)

**Kept only:**
- `exec_slurm_shell()` - SLURM-managed execution (SAFE)

### 2. Strict SLURM Detection (`execution.py`)

```python
def is_slurm_available() -> bool:
    """
    Check if SLURM controller is available and responsive.

    SECURITY: This system requires SLURM for all terminal sessions.
    If SLURM is not available, terminals will be disabled.
    """
```

**Detection criteria:**
1. ✅ `srun` binary exists
2. ✅ SLURM controller responds within 2 seconds
3. ✅ Jobs run immediately (not queued)
4. ✅ Partition configured correctly

**If ANY check fails:** Terminals are DISABLED with error message to user.

### 3. Consumer Enforcement (`consumer.py`)

```python
async def spawn_pty(self):
    """
    Spawn PTY via SLURM + Apptainer (SLURM REQUIRED).

    SECURITY: Terminals are disabled if SLURM is unavailable.
    """

    slurm_available = await asyncio.to_thread(is_slurm_available)

    if not slurm_available:
        # SECURITY: Terminal disabled - no fallback allowed
        error_msg = "╔═══════════════════════════════════╗\n"
        error_msg += "║  TERMINAL UNAVAILABLE             ║\n"
        error_msg += "║  SLURM resource manager required  ║\n"
        error_msg += "╚═══════════════════════════════════╝\n"
        await self.send(text_data=error_msg)
        await self.close()
        return

    # ONLY exec via SLURM - no fallback
    exec_slurm_shell(...)
```

## Security Benefits

### ✅ Resource Isolation
- **CPU limits:** Enforced by SLURM (`--cpus-per-task=2`)
- **Memory limits:** Enforced by SLURM (`--mem=4G`)
- **Time limits:** Enforced by SLURM (`--time=04:00:00`)

### ✅ Fair Scheduling
- **No resource hogging:** SLURM fair-share prevents single user monopolization
- **Priority queues:** Interactive terminals use `express` partition
- **Accounting:** All usage tracked per user/account

### ✅ Container Isolation
- **Apptainer via SLURM:** All containers managed by SLURM jobs
- **No direct execution:** Prevents bypassing resource limits
- **UID preservation:** User runs as themselves inside container

## Configuration

### SLURM Partition Settings

File: `/etc/slurm/slurm.conf`

```bash
PartitionName=express Nodes=... MaxTime=04:00:00 State=UP Priority=100
```

**Must match application settings:**

File: `SECRET/.env.prod`

```bash
SCITEX_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT=04:00:00
SCITEX_QUOTA_SLURM_INTERACTIVE_PARTITION=express
SCITEX_QUOTA_SLURM_INTERACTIVE_CPUS=2
SCITEX_QUOTA_SLURM_INTERACTIVE_MEMORY_GB=4
```

## User Experience

### When SLURM is Available ✅
- Terminal connects instantly
- Full interactive shell via `srun → apptainer`
- Resource limits enforced automatically

### When SLURM is Unavailable ❌
- User sees red error box:
  ```
  ╔═══════════════════════════════════════════════╗
  ║  TERMINAL UNAVAILABLE                         ║
  ║                                               ║
  ║  SLURM resource manager is not responding.    ║
  ║  This is required for security and fairness.  ║
  ║                                               ║
  ║  Please contact support if this persists.     ║
  ╚═══════════════════════════════════════════════╝
  ```
- WebSocket closes gracefully
- Logs: `Terminal denied for {username}: SLURM unavailable`

## Verification

### Check SLURM Status
```bash
# SLURM operational?
sinfo

# Partition configured correctly?
scontrol show partition express | grep MaxTime
# Should show: MaxTime=04:00:00

# Test job submission
timeout 2 srun --pty --partition=express --cpus-per-task=1 --mem=1G true
# Should complete in < 2 seconds
```

### Check Running Terminals
```bash
# All terminals should be SLURM jobs
squeue
# Shows active terminal sessions

# NO direct apptainer processes
ps aux | grep apptainer | grep -v srun
# Should be empty or only show SLURM-managed processes
```

## Troubleshooting

### Terminal Won't Connect

1. **Check SLURM status:**
   ```bash
   systemctl status slurmctld slurmd
   ```

2. **Check partition:**
   ```bash
   scontrol show partition express
   ```

3. **Check Django logs:**
   ```bash
   docker logs scitex-cloud-prod-django-1 | grep -i "slurm\|terminal"
   ```

### Jobs Stuck in Queue

**Symptom:** `(PartitionTimeLimit)` in `squeue`

**Cause:** Job time limit exceeds partition MaxTime

**Fix:**
1. Check partition limit: `scontrol show partition express | grep MaxTime`
2. Check app setting: `grep SCITEX_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT .env.prod`
3. Make them match (partition MaxTime ≥ app time limit)
4. Reload: `sudo scontrol reconfigure`

## Files Changed

1. `apps/code_app/views/terminal/execution.py` - SLURM-only execution
2. `apps/code_app/views/terminal/consumer.py` - SLURM enforcement
3. `deployment/slurm/install-host.sh` - Correct partition MaxTime
4. `deployment/slurm/slurm-docker-{prod,dev}.conf` - Config files
5. `deployment/slurm/CONFIGURATION.md` - Documentation

## Reproducibility

✅ **Fully automated:** Running `sudo ./deployment/slurm/install-host.sh` will:
- Install SLURM with correct partition configuration
- Set express partition MaxTime=04:00:00
- Match application settings in `.env.prod`

No manual configuration needed!

## Security Policy

🔒 **STRICT ENFORCEMENT:**
- All interactive terminals MUST go through SLURM
- No fallbacks to direct execution
- System fails securely (disabled) rather than insecurely (unmanaged)

This is **non-negotiable** for multi-user production environments.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-05
**Author:** System Administrator
