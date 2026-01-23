#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-15 01:00:00 (ywatanabe)"
# File: ./scripts/deployment/backup_workspaces.sh
#
# Simple rsync-based workspace backup script
#
# Purpose:
#   Automatic disaster recovery backups of workspace files
#   Runs every 5 minutes via cron
#
# Architecture:
#   - Does NOT use Git (avoids dirty commits, conflicts)
#   - Simple file-level snapshots
#   - Transparent to users
#   - Admin-only for disaster recovery
#
# Usage:
#   # Manual run
#   ./scripts/deployment/backup_workspaces.sh
#
#   # Cron setup (every 5 minutes)
#   */5 * * * * /app/scripts/deployment/backup_workspaces.sh >> /app/logs/backups.log 2>&1

set -euo pipefail

# Configuration
WORKSPACE_ROOT="${SCITEX_WORKSPACE_ROOT:-/app/data/users}"
BACKUP_ROOT="${SCITEX_BACKUP_ROOT:-/app/backups/snapshots}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAX_SNAPSHOTS="${SCITEX_MAX_SNAPSHOTS:-288}"  # 24 hours at 5-min intervals

# Create backup root if not exists
mkdir -p "$BACKUP_ROOT"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting workspace backups..."

# Counter for statistics
total_workspaces=0
backed_up=0
failed=0

# Iterate through all user workspaces
for user_dir in "$WORKSPACE_ROOT"/*; do
    if [ ! -d "$user_dir" ]; then
        continue
    fi

    username=$(basename "$user_dir")

    for project_dir in "$user_dir"/*; do
        if [ ! -d "$project_dir" ]; then
            continue
        fi

        project=$(basename "$project_dir")
        total_workspaces=$((total_workspaces + 1))

        # Create backup destination
        backup_name="${username}_${project}_${TIMESTAMP}"
        backup_dest="$BACKUP_ROOT/$backup_name"

        # Perform rsync backup
        if rsync -a --delete \
            --exclude='.git/' \
            --exclude='__pycache__/' \
            --exclude='*.pyc' \
            --exclude='node_modules/' \
            --exclude='.venv/' \
            --exclude='venv/' \
            "$project_dir/" "$backup_dest/" >> /dev/null 2>&1; then

            backed_up=$((backed_up + 1))
            echo "  ✓ $username/$project"
        else
            failed=$((failed + 1))
            echo "  ✗ $username/$project (failed)" >&2
        fi
    done
done

# Cleanup old snapshots (keep only MAX_SNAPSHOTS most recent)
echo "Cleaning up old snapshots (keeping $MAX_SNAPSHOTS most recent)..."
snapshot_count=$(ls -1d "$BACKUP_ROOT"/*_* 2>/dev/null | wc -l)

if [ "$snapshot_count" -gt "$MAX_SNAPSHOTS" ]; then
    to_delete=$((snapshot_count - MAX_SNAPSHOTS))
    ls -1dt "$BACKUP_ROOT"/*_* | tail -n "$to_delete" | xargs rm -rf
    echo "  Removed $to_delete old snapshots"
fi

# Summary
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete:"
echo "  Total workspaces: $total_workspaces"
echo "  Backed up: $backed_up"
echo "  Failed: $failed"
echo "  Snapshot: $TIMESTAMP"

exit 0
