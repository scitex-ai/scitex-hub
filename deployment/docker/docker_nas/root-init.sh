#!/bin/bash
# ============================================
# Root-level initialization for NAS deployment
# MUST run as root before dropping to scitex user
# ============================================
set -e

echo "🔒 Running root-level initialization..."

# ============================================
# Fix SLURM UID/GID to match host
# ============================================
if [ -f "/host/etc/passwd" ]; then
    HOST_SLURM_UID=$(grep "^slurm:" /host/etc/passwd 2>/dev/null | cut -d: -f3 || echo "")
    HOST_SLURM_GID=$(grep "^slurm:" /host/etc/passwd 2>/dev/null | cut -d: -f4 || echo "")

    if [ -n "$HOST_SLURM_UID" ] && [ -n "$HOST_SLURM_GID" ]; then
        CONTAINER_SLURM_UID=$(id -u slurm 2>/dev/null || echo "999")

        if [ "$CONTAINER_SLURM_UID" != "$HOST_SLURM_UID" ]; then
            echo "🔧 Syncing SLURM UID: $CONTAINER_SLURM_UID -> $HOST_SLURM_UID"

            # Kill any slurm processes
            pkill -9 -u slurm 2>/dev/null || true

            # Modify group first, then user
            groupmod -g "$HOST_SLURM_GID" slurm 2>/dev/null || true
            usermod -u "$HOST_SLURM_UID" -g "$HOST_SLURM_GID" slurm 2>/dev/null || true

            # Verify
            NEW_UID=$(id -u slurm 2>/dev/null)
            if [ "$NEW_UID" = "$HOST_SLURM_UID" ]; then
                echo "✅ SLURM UID synced: $NEW_UID:$HOST_SLURM_GID"
            else
                echo "⚠️  WARNING: Failed to sync SLURM UID (got $NEW_UID, expected $HOST_SLURM_UID)"
            fi
        else
            echo "✅ SLURM UID already synced: $HOST_SLURM_UID:$HOST_SLURM_GID"
        fi
    else
        echo "⚠️  WARNING: Could not determine host SLURM UID/GID from /host/etc/passwd"
    fi
else
    echo "⚠️  WARNING: /host/etc/passwd not mounted - cannot sync SLURM UID"
fi

# ============================================
# Add scitex user to munge group for authentication
# ============================================
if [ -f "/host/etc/passwd" ]; then
    HOST_MUNGE_GID=$(grep "^munge:" /host/etc/passwd 2>/dev/null | cut -d: -f4 || echo "")

    if [ -n "$HOST_MUNGE_GID" ]; then
        # Create or modify munge group to match host GID
        if ! getent group "$HOST_MUNGE_GID" >/dev/null 2>&1; then
            groupadd -g "$HOST_MUNGE_GID" munge 2>/dev/null || true
        fi

        # Add scitex user to munge group
        if ! id -nG scitex 2>/dev/null | grep -qw "$HOST_MUNGE_GID"; then
            usermod -a -G "$HOST_MUNGE_GID" scitex 2>/dev/null || true
            echo "✅ Added scitex to munge group (GID: $HOST_MUNGE_GID)"
        else
            echo "✅ scitex already in munge group"
        fi
    fi
fi

# ============================================
# Verify critical directories exist
# ============================================
mkdir -p /app/data/slurm /app/logs /app/run
chown -R scitex:scitex /app/data /app/logs /app/run 2>/dev/null || true
chmod -R 755 /app/data/slurm 2>/dev/null || true

echo "✅ Root initialization complete"
echo ""

# Now run the regular entrypoint as scitex user
exec gosu scitex "$@"
