#!/usr/bin/env bash
# install.sh -- Master installer for NAS stability measures
# Run from WSL
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Try LAN-direct first; the bastion route (`nas`) is dead whenever the
# Cloudflare tunnel is down (see health-check.sh).
SSH_HOSTS="${NAS_SSH_HOSTS:-nas-direct nas}"
SSH_HOST=""
SSH_TIMEOUT=10
CRON_SCHEDULE="*/5 * * * *"
HEALTH_CHECK="${SCRIPT_DIR}/health-check.sh"
LOG_FILE="/tmp/nas-health-check.log"

section() {
    echo ""
    echo "========================================"
    echo " $1"
    echo "========================================"
}

check_ssh() {
    local host
    for host in $SSH_HOSTS; do
        echo "Checking SSH connectivity to ${host}..."
        if ssh -o ConnectTimeout="$SSH_TIMEOUT" -o BatchMode=yes "$host" "echo ok" >/dev/null 2>&1; then
            echo "  SSH: OK (${host})"
            SSH_HOST="$host"
            return 0
        fi
        echo "  SSH: FAILED (${host})"
    done
    echo "  Run 'nw-nas' first to establish network route."
    return 1
}

# --- Step 1: Verify SSH ---
section "Step 1: SSH Connectivity"
if ! check_ssh; then
    echo ""
    echo "Cannot proceed without SSH access to NAS."
    echo "Run 'nw-nas' and try again."
    exit 1
fi

# --- Step 2: Deploy and run protect-sshd.sh on NAS ---
section "Step 2: Protect sshd on NAS"
echo "Copying protect-sshd.sh to NAS..."
scp "${SCRIPT_DIR}/protect-sshd.sh" "${SSH_HOST}:/tmp/protect-sshd.sh"

echo "Running protect-sshd.sh on NAS..."
ssh "$SSH_HOST" "chmod +x /tmp/protect-sshd.sh && /tmp/protect-sshd.sh"

# --- Step 3: Deploy diagnose.sh and docker-memory-limits.sh to NAS ---
section "Step 3: Deploy diagnostic scripts to NAS"
echo "Copying scripts to NAS:/opt/scitex/nas-stability/..."
ssh "$SSH_HOST" "mkdir -p /opt/scitex/nas-stability"
scp "${SCRIPT_DIR}/diagnose.sh" "${SSH_HOST}:/opt/scitex/nas-stability/diagnose.sh"
scp "${SCRIPT_DIR}/docker-memory-limits.sh" "${SSH_HOST}:/opt/scitex/nas-stability/docker-memory-limits.sh"
ssh "$SSH_HOST" "chmod +x /opt/scitex/nas-stability/*.sh"
echo "  Deployed: diagnose.sh, docker-memory-limits.sh"

# --- Step 4: Set up cron job on WSL ---
section "Step 4: Install health-check cron job (WSL)"

# Make sure health-check.sh is executable
chmod +x "$HEALTH_CHECK"

# Check if cron job already exists
CRON_LINE="${CRON_SCHEDULE} ${HEALTH_CHECK} >> ${LOG_FILE} 2>&1"
EXISTING=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING" | grep -qF "$HEALTH_CHECK"; then
    echo "  Cron job already exists. Skipping."
else
    echo "$EXISTING" | {
        cat
        echo "$CRON_LINE"
    } | crontab -
    echo "  Installed cron job: ${CRON_LINE}"
fi

# --- Step 5: Verify ---
section "Step 5: Verification"

echo "Checking sshd protection on NAS..."
SCORE=$(ssh "$SSH_HOST" "cat /proc/\$(pgrep -o sshd)/oom_score_adj 2>/dev/null" 2>/dev/null || echo "UNKNOWN")
if [ "$SCORE" = "-1000" ]; then
    echo "  sshd OOM protection: OK (score=${SCORE})"
else
    echo "  sshd OOM protection: NEEDS RESTART (score=${SCORE})"
    echo "  Run on NAS: sudo systemctl restart sshd"
fi

echo ""
echo "Checking cron job..."
if crontab -l 2>/dev/null | grep -qF "$HEALTH_CHECK"; then
    echo "  Cron job: INSTALLED"
else
    echo "  Cron job: MISSING"
fi

echo ""
echo "Checking NAS scripts..."
ssh "$SSH_HOST" "ls -la /opt/scitex/nas-stability/" 2>/dev/null || echo "  WARNING: scripts not found on NAS"

section "Done"
echo "NAS stability measures installed."
echo ""
echo "Next steps:"
echo "  1. Review Docker memory limits: ssh nas '/opt/scitex/nas-stability/docker-memory-limits.sh'"
echo "  2. Monitor health-check log: tail -f ${LOG_FILE}"
echo "  3. Test manually: ${HEALTH_CHECK}"
