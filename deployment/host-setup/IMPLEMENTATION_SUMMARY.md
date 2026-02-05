# Host Setup Automation - Implementation Summary

**Date**: 2025-12-06
**Issue**: Terminal failures with "Error generating job credential"
**Root Cause**: Container UID 1000 (scitex) doesn't exist on host

---

## What Was Implemented

### 1. Automated Validation System

Created comprehensive host requirement checking in `deployment/host-setup/`:

```
deployment/host-setup/
├── checks/              # Non-destructive validation scripts
│   ├── check-users.sh   # Validates UID 1000 (scitex) exists
│   └── check-slurm.sh   # Validates SLURM configuration
├── scripts/             # Setup/modification scripts
│   ├── create-scitex-user.sh  # Creates scitex user (UID 1000)
│   └── lib/
│       └── colors.sh    # Shared color library
└── docs/
    └── README.md        # Full documentation
```

### 2. Makefile Integration

Integrated checks into deployment workflow:

- **`make check-host`**: Run all host validation checks (no ENV required)
- **`make status`**: Now includes host requirement warnings (informational)
- **`make ENV=prod build`**: Shows host requirement warnings before building
- **`make ENV=prod start`**: **BLOCKS** if host requirements not met (hard failure)

### 3. Safety & Automation

- **Informational checks**: `status` and `build` show warnings but don't block
- **Blocking checks**: `start` requires all checks to pass before starting services
- **Clear fix commands**: Each failure provides exact command to resolve it
- **Documentation**: Full README explaining why checks matter and how to fix issues

---

## Why This Is Needed

### The Technical Problem

1. Docker container runs as **UID 1000** (user: scitex)
2. When container submits SLURM job, slurmd validates UID against host `/etc/passwd`
3. If UID 1000 doesn't exist on host → `srun: error: Error generating job credential`
4. Terminal connections fail with "TERMINAL UNAVAILABLE"

### The Fix

**Create scitex user (UID 1000) on the host:**

```bash
sudo deployment/host-setup/scripts/create-scitex-user.sh
```

---

## What You Need To Do

### Step 1: Create scitex User on Host

**Run this command on your production host:**

```bash
sudo deployment/host-setup/scripts/create-scitex-user.sh
```

This will:
- Check if UID 1000 is available
- Create scitex system user with UID 1000
- Verify creation succeeded
- Handle conflicts gracefully
- Show next step (restart SLURM)

### Step 2: Restart SLURM Services

**CRITICAL**: SLURM must be restarted to pick up the new user from `/etc/passwd`

```bash
sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh
```

This will:
- Restart slurmd and slurmctld
- Verify services started successfully
- Confirm SLURM can see the new user

### Step 3: Test Terminal Connection (Optional)

**Verify everything is working:**

```bash
deployment/host-setup/scripts/test-terminal-connection.sh
```

This will:
- Check scitex user exists
- Check SLURM services running
- Check Django container running
- **Test actual SLURM job submission** from container
- Report if terminals will work

### Step 4: Verify Host Requirements

```bash
make check-host
```

Expected output after user creation:
```
✓ User 'scitex' exists with correct UID 1000
✓ slurmd service is running
✓ slurmctld service is running
✓ express partition MaxTime is correct: 04:00:00
✓ munge service is running
✓ munge.key exists (verified by running munge service)
```

### Step 5: Test Terminals

1. Open https://scitex.ai
2. Navigate to a project
3. Click "Terminal" tab
4. Terminal should connect successfully
5. You should see a working bash prompt

---

## Future Usage

### Every Deployment

The checks are now **automatic**:

- **`make ENV=prod status`**: Shows current host status with warnings
- **`make ENV=prod start`**: Validates requirements before starting (BLOCKS if failed)
- **`make ENV=prod build`**: Shows informational warnings during build
- **`make check-host`**: Manual check anytime

### Adding New Checks

See `deployment/host-setup/docs/README.md` for instructions on:
- Adding new validation scripts
- Integrating with Makefile
- Following naming conventions
- Using shared color library

---

## Troubleshooting

### "UID 1000 is already taken"

If another user has UID 1000:

1. Check who: `id 1000`
2. Options:
   - Reassign that user to different UID
   - Change container UID (not recommended)
   - Manually resolve conflict

### "Permission denied" Running Scripts

```bash
chmod +x deployment/host-setup/checks/*.sh
chmod +x deployment/host-setup/scripts/*.sh
chmod +x deployment/host-setup/scripts/lib/*.sh
```

### Terminals Still Failing After User Creation

1. Verify: `id scitex` → should show `uid=1000(scitex)`
2. Test SLURM: `srun --uid=1000 whoami` → should print "scitex"
3. Test from container:
   ```bash
   docker exec scitex-cloud-prod-django-1 su scitex -c "srun --partition=express --pty true"
   ```
4. Check logs: `docker logs scitex-cloud-prod-django-1 --tail 50`

---

## Files Changed

### Created
- `deployment/host-setup/checks/check-users.sh`
- `deployment/host-setup/checks/check-slurm.sh`
- `deployment/host-setup/scripts/create-scitex-user.sh`
- `deployment/host-setup/scripts/lib/colors.sh`
- `deployment/host-setup/docs/README.md`
- `deployment/host-setup/IMPLEMENTATION_SUMMARY.md` (this file)

### Modified
- `Makefile`: Added `check-host` target and integrated with `start`, `status`, `build`

---

## Summary

**Problem**: Terminal failures due to missing UID 1000 on host
**Solution**: Automated checking + clear fix scripts
**Next Step**: Run `sudo deployment/host-setup/scripts/create-scitex-user.sh`

The automation ensures this won't be forgotten in future deployments - checks run automatically during `make ENV=prod start`.
