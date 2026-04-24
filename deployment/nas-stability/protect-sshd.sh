#!/usr/bin/env bash
# protect-sshd.sh -- Make sshd immune to the OOM killer
# Run on the NAS (directly or via SSH from install.sh)
set -euo pipefail

OVERRIDE_DIR="/etc/systemd/system/sshd.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/oom-protect.conf"

echo "[protect-sshd] Protecting sshd from OOM killer..."

# --- Create override directory ---
if [ ! -d "$OVERRIDE_DIR" ]; then
    sudo mkdir -p "$OVERRIDE_DIR"
    echo "[protect-sshd] Created ${OVERRIDE_DIR}"
fi

# --- Write override ---
sudo tee "$OVERRIDE_FILE" >/dev/null <<'UNIT'
[Service]
OOMScoreAdjust=-1000
UNIT
echo "[protect-sshd] Wrote ${OVERRIDE_FILE}"

# --- Reload systemd ---
sudo systemctl daemon-reload
echo "[protect-sshd] Reloaded systemd daemon"

# --- Verify ---
SCORE=$(cat "/proc/$(pgrep -o sshd)/oom_score_adj" 2>/dev/null || echo "UNKNOWN")
if [ "$SCORE" = "-1000" ]; then
    echo "[protect-sshd] SUCCESS: sshd OOM score is ${SCORE} (protected)"
else
    echo "[protect-sshd] WARNING: sshd OOM score is ${SCORE}"
    echo "[protect-sshd] A restart of sshd is needed for the override to take effect."
    echo "[protect-sshd] Run: sudo systemctl restart sshd"
    echo "[protect-sshd] (This will NOT drop your current SSH session.)"
fi
