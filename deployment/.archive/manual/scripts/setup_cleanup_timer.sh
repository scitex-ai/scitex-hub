#!/bin/bash
# Setup systemd timer for automatic cleanup of stale BibTeX jobs
# This prevents malicious attacks and resource exhaustion

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="${SCRIPT_DIR}/../systemd"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=== SciTeX Scholar - Setting up automatic job cleanup ==="

# Create user systemd directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Copy service and timer files
echo "Installing systemd service and timer..."
cp "${SYSTEMD_DIR}/scitex-cleanup-jobs.service" "$SYSTEMD_USER_DIR/"
cp "${SYSTEMD_DIR}/scitex-cleanup-jobs.timer" "$SYSTEMD_USER_DIR/"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start the timer
echo "Enabling and starting cleanup timer..."
systemctl --user enable scitex-cleanup-jobs.timer
systemctl --user start scitex-cleanup-jobs.timer

# Show status
echo ""
echo "=== Status ==="
systemctl --user status scitex-cleanup-jobs.timer --no-pager

echo ""
echo "=== Timer Schedule ==="
systemctl --user list-timers scitex-cleanup-jobs.timer --no-pager

echo ""
echo "✓ Setup complete!"
echo ""
echo "The cleanup job will run:"
echo "  - Every 5 minutes to fail stale jobs"
echo "  - Automatically delete jobs older than 30 days"
echo ""
echo "Useful commands:"
echo "  systemctl --user status scitex-cleanup-jobs.timer   # Check timer status"
echo "  systemctl --user stop scitex-cleanup-jobs.timer     # Stop timer"
echo "  systemctl --user start scitex-cleanup-jobs.timer    # Start timer"
echo "  journalctl --user -u scitex-cleanup-jobs            # View logs"
echo "  python manage.py cleanup_stale_jobs --dry-run       # Test manually"
