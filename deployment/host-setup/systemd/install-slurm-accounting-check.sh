#!/bin/bash
# Install the SLURM accounting health check and its 10-minute timer.
#
# Usage: sudo ./install-slurm-accounting-check.sh   (on the accounting host, scitex-compute-01)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo "Error: Must run as root (sudo)" >&2
    exit 1
fi

install -m 0755 "${SCRIPT_DIR}/../checks/check-slurm-accounting.sh" /usr/local/sbin/scitex-check-slurm-accounting
install -m 0644 "${SCRIPT_DIR}/scitex-slurm-accounting-check.service" /etc/systemd/system/
install -m 0644 "${SCRIPT_DIR}/scitex-slurm-accounting-check.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now scitex-slurm-accounting-check.timer

# Run once now and report the real result.
if systemctl start scitex-slurm-accounting-check.service; then
    echo "✓ SLURM accounting check installed and passing"
else
    echo "❌ SLURM accounting check installed and FAILING — journalctl -u scitex-slurm-accounting-check -n 40" >&2
    exit 1
fi
