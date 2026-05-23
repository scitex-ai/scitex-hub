# Host Setup Scripts

Automated scripts for setting up and validating the NAS host environment for SciTeX Cloud.

## Directory Structure

```
deployment/host-setup/
├── checks/              # Validation scripts (non-destructive)
│   ├── check-users.sh          # Validate required system users exist
│   ├── check-slurm.sh          # Validate SLURM configuration
│   └── check-terminal-ready.sh # Test actual terminal functionality
├── scripts/             # Setup/modification scripts
│   ├── create-scitex-user.sh            # Create scitex system user
│   ├── restart-slurm-for-new-user.sh    # Restart SLURM after user creation
│   ├── test-terminal-connection.sh      # Test if terminals will work
│   └── lib/             # Shared libraries
│       └── colors.sh    # Terminal colors and logging
└── docs/
    └── README.md        # This file
```

## Quick Start

### Run All Checks

```bash
make ENV=prod check-host
```

### Fix Common Issues

#### Missing scitex User (UID 1000)

**Problem**: Terminals fail with "Error generating job credential"

**Cause**: SLURM requires users to exist on compute nodes for credential validation

**Fix** (2 steps):
```bash
# Step 1: Create the scitex user
sudo deployment/host-setup/scripts/create-scitex-user.sh

# Step 2: Restart SLURM to pick up the new user
sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh

# Step 3 (optional): Test that terminals will work
deployment/host-setup/scripts/test-terminal-connection.sh
```

## Integration with Makefile

All host checks are automatically run during:
- `make ENV=prod status` - Shows current status with warnings
- `make ENV=prod start` - Checks before starting services
- `make ENV=prod build` - Validates host before building

## Check Scripts

### check-users.sh

Validates:
- scitex user exists with UID 1000
- No UID conflicts
- Provides fix commands if issues found

Exit codes:
- 0: All checks passed
- 1: One or more checks failed

### check-slurm.sh

Validates:
- slurmd and slurmctld are running
- express partition has MaxTime=04:00:00
- munge service is running
- munge.key exists with correct permissions

## Setup Scripts

### create-scitex-user.sh

Creates the scitex system user (UID 1000) required for SLURM job execution.

**Must run as root**: `sudo deployment/host-setup/scripts/create-scitex-user.sh`

## Why These Checks Matter

### scitex User Requirement

The Docker container runs as UID 1000 (scitex). When submitting SLURM jobs from the container:

1. Container process (UID 1000) calls `srun`
2. SLURM allocates job with UID 1000
3. slurmd validates the UID exists on the compute node
4. If UID 1000 doesn't exist → "Error generating job credential"

**Solution**: The scitex user (UID 1000) must exist on all SLURM compute nodes.

### SLURM Partition Time Limits

The express partition is used for interactive terminals. If MaxTime < 04:00:00:
- Jobs get queued with `(PartitionTimeLimit)`
- Terminals connect then immediately disconnect
- Users see connection loops

**Solution**: express partition must have MaxTime=04:00:00 or greater.

## Adding New Checks

1. Create check script in `checks/` directory
2. Follow naming: `check-<component>.sh`
3. Source `lib/colors.sh` for consistent output
4. Return exit code 0 (success) or 1 (failure)
5. Add to `Makefile` target `check-host`

Example:
```bash
#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/../scripts/lib/colors.sh"

echo -e "${BLUE}Checking something...${NC}"
if [ condition ]; then
    echo -e "${GREEN}✓ Check passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Check failed${NC}"
    echo -e "${YELLOW}  Fix: command to fix${NC}"
    exit 1
fi
```

## Troubleshooting

### Terminals Still Failing After Creating scitex User

1. Verify user was created correctly:
   ```bash
   id scitex
   # Should show: uid=1000(scitex) ...
   ```

2. Check SLURM can see the user:
   ```bash
   srun --uid=1000 whoami
   # Should succeed and print: scitex
   ```

3. Test from container:
   ```bash
   docker exec scitex-hub-prod-django-1 su scitex -c "srun --partition=express --pty true"
   # Should succeed with no errors
   ```

### Permission Denied Errors

If you see "Permission denied" when running setup scripts:

```bash
chmod +x deployment/host-setup/checks/*.sh
chmod +x deployment/host-setup/scripts/*.sh
chmod +x deployment/host-setup/scripts/lib/*.sh
```
