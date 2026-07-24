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
# Always create .scitex/hub/runtime directory (LOG_DIR default for the
# Django/Celery app itself -- config/settings/settings_logging.py resolves
# LOG_DIR here via scitex_config's runtime-state-db-layout convention.
# A fallback default must NEVER again point at a directory nothing
# guarantees exists -- see incident hub-prod-outage-celery-log-permission
# (2026-07-09/10, ~90min prod outage from celery_file PermissionError).
mkdir -p /app/.scitex/hub/runtime
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
#
# uv_cache_volume / npm_cache_volume are SHARED (UV_CACHE_DIR=/app/.cache/uv)
# across django AND the celery_{worker,beat} services. The celery services
# override the compose `entrypoint:` to skip root-init.sh, i.e. they run this
# image's entrypoint — and its install_apps.sh — AS ROOT. A root-run
# `uv pip install` therefore seeds the shared cache with ROOT-OWNED subpaths
# (e.g. .cache/uv/sdists-v9/.git). A plain `stat` of the TOP-LEVEL
# /app/.cache/uv still reads "scitex" (fixed on an earlier boot) while those
# root-owned files sit DEEPER in the tree, so a top-level-only guard skips the
# chown; django's scitex-user `uv` then dies with
#   "Failed to initialize cache ... /app/.cache/uv/sdists-v9/.git:
#    Permission denied (os error 13)"
# and install_apps.sh falls back to pip (which then also fails — see the
# /usr/local/bin fix below), aborting the editable install and leaving the
# stale baked wheel to break the boot-time vite build (daphne never binds ->
# 503 crash-loop). So probe RECURSIVELY for any non-scitex file (cheap:
# `find -print -quit` stops at the first hit) and chown -R only when
# contamination is actually found — same idiom as the staticfiles block below.
#
# NOTE (2026-07-11): this chown is now the BELT, not the fix. The DEFINITIVE
# fix is the celery guard in entrypoint-prod.sh, which stops celery_{worker,
# beat} from ever running install_apps.sh's `uv pip install`. With that guard,
# django (the scitex user) is the ONLY writer of this cache, so nothing
# re-contaminates it concurrently and this one-time sweep decisively cleans
# any LEGACY root-owned files a pre-fix celery boot already left in the shared
# volume (and covers a brand-new volume whose mountpoint first appears
# root-owned). Before that guard, celery re-seeded the cache in parallel with
# this chown every boot (shared volume + restart:always), so the chown kept
# losing the race — which is why PR #346's chown alone never made uv succeed.
mkdir -p /app/.cache/uv /app/.cache/npm
for cache_dir in /app/.cache/uv /app/.cache/npm; do
    FOREIGN_CACHE=$(find "$cache_dir" ! -user scitex -print -quit 2>/dev/null)
    if [ -n "$FOREIGN_CACHE" ]; then
        echo "🔧 Fixing $cache_dir ownership (found non-scitex file: $FOREIGN_CACHE)..."
        chown -R scitex:scitex "$cache_dir"
    fi
done
echo "✅ uv/npm cache directories ready"

# ============================================
# Fix system site-packages ownership (uv --system editable installs)
# ============================================
# install_apps.sh (running as scitex) uses `uv pip install --system -e ...`
# to replace the image's pinned PyPI siblings (scitex-ui, figrecipe,
# scitex-writer, scitex-todo, scitex-storage) with live-tracking editable
# checkouts.
#
# This block used to chown ONLY the top-level site-packages directory, on the
# reasoning that "POSIX create/delete permission is governed by the containing
# directory". That rule is real, but it was applied to the wrong directory: a
# package is a DIRECTORY TREE, and replacing figrecipe means unlinking
# site-packages/figrecipe/WHEEL — whose containing directory is figrecipe/,
# which stayed ROOT-owned (Dockerfile.prod installs the pinned wheels as root).
# So every prod boot, uv died with
#     [Errno 13] Permission denied: 'WHEEL'
# fell back to slow plain pip, blew the 300s APP_INSTALL_TIMEOUT, and was
# SIGTERM'd part-way down .scitex-apps.json. Apps LATER in the list were never
# installed at all (2026-07-13: scitex-storage is last — /apps/storage/ 404'd
# and its tile never appeared), and the earlier ones silently kept resolving to
# the STALE PINNED WHEEL instead of the develop checkout this script exists to
# install. Confirmed live: 130,409 of ~130,421 site-packages entries root-owned.
#
# The DURABLE fix is in Dockerfile.prod (the site-packages COPY carries
# --chown, and the root-run `uv pip install` layers chown their delta), so a
# freshly built image already ships scitex-owned packages and the sweep below
# finds nothing. What remains here is the BELT: it repairs an image built
# before that fix, and catches a regression if a future root-context install
# layer re-contaminates the tree.
SITE_PACKAGES="/usr/local/lib/python3.11/site-packages"
if [ -d "$SITE_PACKAGES" ]; then
    # Debris from a SIGTERM'd install: uv/pip stage a replacement package as
    # `~<name>` and rename it into place at the end. A killed install strands
    # the `~` stub, and pip then warns "Ignoring invalid distribution" on every
    # later run — self-perpetuating. (Live right now: ~citex_ui-0.6.4.dist-info.)
    if compgen -G "$SITE_PACKAGES/~*" >/dev/null 2>&1; then
        echo "🔧 Removing interrupted-install debris from site-packages..."
        rm -rf "${SITE_PACKAGES:?}"/~*
    fi

    # Creating/removing a TOP-LEVEL entry needs write on site-packages itself.
    if [ "$(stat -c '%U' "$SITE_PACKAGES" 2>/dev/null)" != "scitex" ]; then
        chown scitex:scitex "$SITE_PACKAGES"
    fi

    # ...and REPLACING a package needs write on that package's OWN directory,
    # recursively. Skip anything on a different filesystem: docker-compose
    # bind-mounts host paths READ-ONLY *inside* site-packages (scitex_container,
    # scitex/scholar/citation_graph). Neither is scitex-owned (uid 1001 / root),
    # so a plain `! -user scitex` sweep would try to chown them, fail EROFS, and
    # — under `set -e` — crash-loop the container. Filtering on find's device id
    # (%D) skips the mount points AND everything beneath them without hardcoding
    # their paths, so a new :ro bind in compose cannot silently break boot.
    # Measured on live prod: the full walk is ~230ms over 130k entries, so this
    # is cheap enough to assert on every boot rather than trust the image.
    SP_DEV=$(stat -c '%d' "$SITE_PACKAGES")
    # Emit the same-device, non-scitex paths. `substr($0, index($0, "\t") + 1)`
    # takes everything after the first tab, so it is correct even if a path
    # itself contained a tab; it is also mawk-compatible (this image is Debian
    # slim — gawk-only constructs like RS="\0" are not available here).
    sp_foreign() {
        find "$SITE_PACKAGES" -xdev ! -user scitex -printf '%D\t%p\n' 2>/dev/null \
            | awk -F'\t' -v dev="$SP_DEV" '$1 == dev { print substr($0, index($0, "\t") + 1) }'
    }
    # Cheap probe first. `head -n 1` closes the pipe after one line, so awk and
    # find are SIGPIPE'd and stop walking rather than listing all ~130k entries.
    FOREIGN_FIRST=$(sp_foreign | head -n 1)
    if [ -n "$FOREIGN_FIRST" ]; then
        echo "🔧 Fixing site-packages ownership (e.g. $FOREIGN_FIRST)..."
        # Stream into xargs rather than materializing 130k paths in a shell var.
        if sp_foreign | xargs -d '\n' --no-run-if-empty chown scitex:scitex; then
            echo "✅ site-packages ownership fixed"
        else
            # Loud, but NOT fatal: a failure here degrades to "some workspace
            # apps are missing" (visible as a 404 + absent tile), whereas
            # exiting would crash-loop the whole site. Never silently swallowed.
            echo "❌ ERROR: could not chown site-packages — editable app installs WILL fail," >&2
            echo "   so workspace apps will silently fall back to their stale pinned wheels." >&2
            echo "   Hint: check for read-only (:ro) mounts under $SITE_PACKAGES in" >&2
            echo "   deployment/docker/docker-compose.*.yml — they must sit on a different" >&2
            echo "   device than $SITE_PACKAGES (dev $SP_DEV) for the filter above to skip them." >&2
        fi
    else
        echo "✅ site-packages ownership OK"
    fi
fi

# ============================================
# Fix /usr/local/bin ownership (editable-install console scripts)
# ============================================
# Editable-installing the sibling apps also (re)writes their console-script
# entry points under /usr/local/bin (scitex-ui, scitex-todo, ...). Those
# scripts — and /usr/local/bin itself — are baked ROOT-OWNED into the image
# (Dockerfile.prod installs the pinned PyPI siblings as root). The scitex user
# can then neither overwrite nor unlink+recreate them, so the install dies with
# e.g. "Permission denied: '/usr/local/bin/scitex-ui'". This hits BOTH uv and
# the pip fallback (uv/pip uninstall-then-reinstall, rewriting the script) —
# it is the second half of the same boot-blocking cascade as the uv-cache
# failure above. As with site-packages, creating/replacing an entry only needs
# WRITE on the CONTAINING directory (POSIX create/unlink/rename is governed by
# the directory, not the target file's own mode), so a single NON-recursive
# chown of /usr/local/bin suffices: the binaries inside stay root-owned and
# world-executable; scitex just gains the ability to swap the app entry points
# (which are re-generated on every editable install, so they stay functional).
BIN_DIR="/usr/local/bin"
if [ -d "$BIN_DIR" ] && [ "$(stat -c '%U' "$BIN_DIR" 2>/dev/null)" != "scitex" ]; then
    echo "🔧 Fixing $BIN_DIR ownership for editable-install console scripts..."
    chown scitex:scitex "$BIN_DIR"
    echo "✅ /usr/local/bin ownership fixed (top-level only, non-recursive)"
else
    echo "✅ /usr/local/bin ownership OK"
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
