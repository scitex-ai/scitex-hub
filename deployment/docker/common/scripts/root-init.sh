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

# ============================================
# Fix scitex config directory permissions (for logging)
# ============================================
# Always create .scitex/logs directory (required by scitex package)
mkdir -p /app/.scitex/logs
chown -R scitex:scitex /app/.scitex 2>/dev/null || true
chmod -R 755 /app/.scitex 2>/dev/null || true
echo "✅ .scitex directory permissions fixed"

# ============================================
# Fix user data directory permissions
# ============================================
# NAS bind mounts can lose permissions (show as d--------- inside container)
# This fixes permissions on startup to ensure user directories are accessible
if [ -d "/app/data/users" ]; then
    # Check if any user directory has broken permissions
    BROKEN_PERMS=$(find /app/data/users -maxdepth 2 -type d ! -perm -755 2>/dev/null | head -1)
    if [ -n "$BROKEN_PERMS" ]; then
        echo "🔧 Fixing user data directory permissions (NAS bind mount issue)..."
        chmod -R 755 /app/data/users 2>/dev/null || true
        chown -R scitex:scitex /app/data/users 2>/dev/null || true
        echo "✅ User data permissions fixed"
    else
        echo "✅ User data permissions OK"
    fi
fi

# ============================================
# Fix node_modules permissions (built as root in Docker image)
# ============================================
if [ -d "/app/node_modules" ] && [ "$(stat -c '%U' /app/node_modules 2>/dev/null)" = "root" ]; then
    echo "🔧 Fixing node_modules ownership (root -> scitex)..."
    chown -R scitex:scitex /app/node_modules
    # Clean stale npm temp dirs from previous failed installs
    find /app/node_modules -maxdepth 1 -name '.*' -type d ! -name '.bin' ! -name '.' -exec rm -rf {} + 2>/dev/null || true
    echo "✅ node_modules permissions fixed"
fi

# ============================================
# Fix /app/.apps volume ownership (sibling dev-installs)
# ============================================
# apps_volume may be created fresh (new deploy, or first time added to an
# environment) — a brand-new named volume's mount point defaults to
# root:root before anything has written to it. install_apps.sh runs as
# the scitex user (after this script gosu's down) and needs to clone into
# and create subdirectories here (2026-07-10, hub-postboot-warmup-window).
mkdir -p /app/.apps
if [ "$(stat -c '%U' /app/.apps 2>/dev/null)" != "scitex" ]; then
    echo "🔧 Fixing /app/.apps ownership (root -> scitex)..."
    chown -R scitex:scitex /app/.apps
    echo "✅ /app/.apps ownership fixed"
else
    echo "✅ /app/.apps ownership OK"
fi

# ============================================
# Fix uv/npm runtime cache volume ownership
# ============================================
# Persistent cache volumes for install_apps.sh's `uv pip install` / `npm
# install` calls, so a re-install (fresh clone, or a genuine dependency
# bump) reuses previously-downloaded packages instead of re-fetching from
# the network every time (operator directive, 2026-07-08).
mkdir -p /app/.cache/uv /app/.cache/npm
for cache_dir in /app/.cache/uv /app/.cache/npm; do
    if [ "$(stat -c '%U' "$cache_dir" 2>/dev/null)" != "scitex" ]; then
        echo "🔧 Fixing $cache_dir ownership (root -> scitex)..."
        chown -R scitex:scitex "$cache_dir"
    fi
done
echo "✅ uv/npm cache directories ready"

# ============================================
# Fix system site-packages top-level ownership (uv --system editable installs)
# ============================================
# install_apps.sh (running as scitex) uses `uv pip install --system -e ...`
# to replace the image's pinned PyPI siblings (scitex-ui, figrecipe,
# scitex-writer, ...) with live-tracking editable checkouts. Creating or
# replacing a package's dist-info entry only needs WRITE access to the
# site-packages DIRECTORY itself — POSIX create/delete permission is
# governed by the containing directory, not the target file's own
# ownership — so this is a single non-recursive chown, not a slow walk of
# the (large, torch/scipy-sized) existing tree.
SITE_PACKAGES="/usr/local/lib/python3.11/site-packages"
if [ -d "$SITE_PACKAGES" ] && [ "$(stat -c '%U' "$SITE_PACKAGES" 2>/dev/null)" != "scitex" ]; then
    echo "🔧 Fixing site-packages ownership for uv --system editable installs..."
    chown scitex:scitex "$SITE_PACKAGES"
    echo "✅ site-packages ownership fixed (top-level only, non-recursive)"
else
    echo "✅ site-packages ownership OK"
fi

# ============================================
# Fix staticfiles volume ownership
# ============================================
# The static volume can accumulate files owned by other UIDs (e.g.
# root-owned figrecipe/index.html from an earlier root-context write).
# collectstatic (running as scitex) then dies with PermissionError on
# delete and — because the entrypoint runs `set -e` — the container
# crash-loops before the visitor-pool reconcile ever runs
# (observed 2026-07-08: 11 restarts on
# '/app/staticfiles/figrecipe/index.html').
if [ -d "/app/staticfiles" ]; then
    FOREIGN_STATIC=$(find /app/staticfiles ! -user scitex -print -quit 2>/dev/null)
    if [ -n "$FOREIGN_STATIC" ]; then
        echo "🔧 Fixing staticfiles ownership (found non-scitex file: $FOREIGN_STATIC)..."
        chown -R scitex:scitex /app/staticfiles
        echo "✅ staticfiles ownership fixed"
    else
        echo "✅ staticfiles ownership OK"
    fi
fi

# ============================================
# Fix Vite staticfiles permissions
# ============================================
# Clean stale vite output so the scitex user can rebuild fresh.
# The build step in entrypoint will recreate this directory.
if [ -d "/app/staticfiles/vite" ]; then
    rm -rf /app/staticfiles/vite
    echo "✅ Vite staticfiles cleaned (will rebuild)"
else
    echo "✅ Vite staticfiles permissions fixed"
fi

echo "✅ Root initialization complete"
echo ""

# Now run the regular entrypoint as scitex user
exec gosu scitex "$@"
