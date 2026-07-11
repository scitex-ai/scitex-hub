#!/bin/bash
set -e

# ============================================
# Production Environment Entrypoint
# ============================================

# Source common libraries
source /app/deployment/docker/common/lib/logging.src
source /app/deployment/docker/common/lib/database.src
source /app/deployment/docker/common/lib/django.src
source /app/deployment/docker/common/lib/scitex.src
source /app/deployment/docker/common/lib/slurm.src

echo -e "🏭 NAS Environment"

# ============================================
# Sync SLURM UID with Host (Required for Terminal)
# ============================================
sync_slurm_uid || echo_warning "SLURM UID sync skipped - terminal may have issues"

# ============================================
# Verify SciTeX from PyPI
# ============================================
verify_scitex_package

# Ensure we're NOT using editable install
if [ -d "/scitex-code" ]; then
    echo -e "⚠️  WARNING: /scitex-code detected in production!"
    echo -e "   This should not be mounted in prod/nas environments."
    echo -e "   Using PyPI version anyway..."
fi

# ============================================
# Database & Django Setup
# ============================================
wait_for_database
run_migrations
# collectstatic ONLY in the web container. The celery services reuse this
# entrypoint but run AS ROOT (compose overrides the entrypoint without
# root-init.sh/gosu) and celery_worker mounts the shared static_volume —
# a root collectstatic there poisons the volume with root-owned files
# (e.g. figrecipe/index.html, 2026-07-08) that the scitex-user
# collectstatic in django-1 cannot delete, crash-looping the web
# container before the visitor-pool reconcile ever runs.
if [[ ! "$*" =~ "celery" ]]; then
    collect_static_files
else
    echo_info "Skipping collectstatic (celery service)"
fi

# ============================================
# Initialize Visitor Pool (web container ONLY)
# ============================================
# NEVER in celery services: they run this entrypoint as root, and a
# root-run reconcile wipes + re-clones visitor workspaces as root,
# leaving root-owned files under /app/data/users that the scitex-user
# wipe cannot remove later (the original PermissionError('revision.tex')
# failure mode the quarantine fail-safe was built against).
if [[ ! "$*" =~ "celery" ]]; then
    echo_info "Initializing visitor pool..."
    python manage.py create_visitor_pool --verbosity 0 2>&1 | grep -v "ERRO\|WARN" || true
    # Boot fail-safe: quarantine every slot as unverified (synchronous,
    # DB-only), then ENQUEUE the per-slot wipe+verify re-clean to Celery via
    # --async. This takes the multi-minute clone loop OFF the web-serving
    # startup path so Django serves immediately (the old inline reconcile left
    # django-1 "Up (unhealthy)" for minutes after a deploy). Slots stay
    # quarantined (not allocatable) until a worker verifies each clean —
    # visitors get the readonly-visitor fallback during the async window, so
    # visitor-slot isolation is unchanged.
    python manage.py reconcile_visitor_slots --async 2>&1 | grep -v "ERRO\|WARN" || true
    echo_success "Visitor pool ready (re-clean dispatched async; only verified-clean slots distributable)"
else
    echo_info "Skipping visitor pool init (celery service)"
fi

# ============================================
# Install Workspace Apps (bridge resolution)
# ============================================
# install_apps.sh clones the sibling app repos into /app/.apps (the Vite
# bridge build below scans them — see the .apps/*/_django/frontend/src check
# in VITE_REBUILD_NEEDED) and editable-installs them. It sits on the CRITICAL
# PATH to `exec daphne`, so it must never be able to block boot indefinitely.
# Failure modes that leave daphne unbound and the container un-healthy forever
# (the 2026-07 prod outage + staging crash-loop): a hung git clone / ls-remote,
# a slow plain-pip editable fallback, a stalled npm install, or — because
# django + celery_{worker,beat} share the /app/.apps volume — a peer wedged
# under install_apps.sh's own `flock -w 600` (a 10-min wait).
#
# Two independent guards make daphne start regardless of outcome:
#   * `|| echo_warning`  — a FAILED install is non-fatal (already present).
#   * `timeout`          — a HUNG install is converted into a (caught) non-zero
#                          exit, so the entrypoint always proceeds to daphne.
# Killing the wrapper also closes fd 200, releasing install_apps.sh's flock so
# a shared-volume peer is never left blocked on a dead lock holder.
#
# The bound (default 300s) is env-overridable (APP_INSTALL_TIMEOUT_SECONDS —
# mirrors the BOOT_GRACE_SECONDS / RESTART_COOLDOWN_SECONDS pattern in
# deployment/nas-stability/health-check.sh) and is deliberately well under the
# watchdog boot-grace (BOOT_GRACE_SECONDS=720), so even a full timeout still
# lets daphne bind and pass its health check on the SAME boot instead of being
# blanket-restarted mid-install. --kill-after SIGKILLs a child that ignores the
# initial SIGTERM. NOTE: the uv-cache / site-packages / .apps volume perms that
# used to force the slow plain-pip fallback are fixed separately in
# root-init.sh; this guard is the structural backstop for ANY residual hang.
echo_info "Installing workspace apps for Vite bridge resolution..."
APP_INSTALL_TIMEOUT="${APP_INSTALL_TIMEOUT_SECONDS:-300}"
timeout --kill-after=10s "${APP_INSTALL_TIMEOUT}" \
    bash /app/scripts/apps/install_apps.sh 2>&1 \
    || echo_warning "App install failed or exceeded ${APP_INSTALL_TIMEOUT}s — continuing to daphne (Vite build may miss some app bridges)"

# ============================================
# Conditional NPM Install & TypeScript Build
# ============================================
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.install-timestamp" ]; then
    echo_info "Installing npm dependencies (including dev for Vite build)..."
    # Note: node_modules ownership fix is handled by root-init.sh (runs as root)
    npm install
    touch node_modules/.install-timestamp
    echo_success "npm dependencies installed"
else
    echo_info "npm dependencies already up to date"
fi

# Build TypeScript files with Vite (production build)
# Note: Vite staticfiles permissions are fixed in root-init.sh (runs as root)

# Check if build is needed by comparing source files vs build output
VITE_REBUILD_NEEDED=false
if [ ! -d "staticfiles/vite" ]; then
    VITE_REBUILD_NEEDED=true
elif [ "vite.config.ts" -nt "staticfiles/vite/.build-timestamp" ]; then
    VITE_REBUILD_NEEDED=true
elif [ -n "$(find static apps -name '*.ts' -newer staticfiles/vite/.build-timestamp 2>/dev/null | head -1)" ]; then
    # Check if any TS source file is newer than the build (in static/ and apps/)
    VITE_REBUILD_NEEDED=true
elif [ -n "$(find .apps -name node_modules -prune -o -name '.git' -prune -o -path '*/_django/frontend/src/*' -name '*.ts' -newer staticfiles/vite/.build-timestamp -print 2>/dev/null | head -1)" ]; then
    # Sibling app bridges (vite.config.ts's discoverAppBridges() scans
    # .apps/*/src/*/_django/frontend/src for a manifest "bridge" entry —
    # see scitex-todo's manifest.json). install_apps.sh clones these
    # OUTSIDE static/ and apps/, so the check above never sees them; a
    # freshly-cloned sibling's bridge silently never got Vite-bundled on
    # a plain container restart (only a full deploy via
    # scripts/deploy/rebuild.sh caught it, since that script
    # unconditionally clears .build-timestamp). Pruned to node_modules/
    # .git and the _django/frontend/src bridge path so this stays cheap
    # instead of walking every sibling's full checkout.
    VITE_REBUILD_NEEDED=true
fi

if [ "$VITE_REBUILD_NEEDED" = true ]; then
    # Clean stale vite output dir completely before rebuild.
    # collectstatic (which runs earlier) may copy old vite files with different
    # ownership, causing EACCES when Vite tries to emptyDir before writing.
    if [ -d "staticfiles/vite" ]; then
        rm -rf staticfiles/vite
    fi
    echo_info "Building TypeScript files with Vite..."
    npm run build
    touch staticfiles/vite/.build-timestamp
    echo_success "TypeScript build complete"
    # Re-run collectstatic to pick up new vite output
    # NOTE: Do NOT use --clear here - it would delete the vite output!
    echo_info "Collecting static files (post-vite)..."
    python manage.py collectstatic --noinput 2>&1 | tail -1
    echo_success "Static files collected"
else
    echo_info "TypeScript build already up to date"
fi

# ============================================
# Start Terminal Broker (Background) - Only for main Django app
# ============================================
# The terminal broker runs PTY operations in a separate process from Daphne
# to prevent asyncio/signal conflicts that can cause deadlocks
if [[ ! "$*" =~ "celery" ]]; then
    echo_info "Starting terminal broker..."
    python manage.py run_terminal_broker &
    TERMINAL_BROKER_PID=$!
    sleep 1
    if kill -0 $TERMINAL_BROKER_PID 2>/dev/null; then
        echo_success "Terminal broker started (PID: $TERMINAL_BROKER_PID)"
    else
        echo_warning "Terminal broker failed to start - will use fallback mode"
    fi
else
    echo_info "Skipping terminal broker (celery worker)"
fi

# ============================================
# Start SSH Gateway (Background) - Only for main Django app
# ============================================
# Skip SSH gateway for celery workers - they don't need it
if [[ ! "$*" =~ "celery" ]]; then
    echo_info "Starting SSH gateway on port 2200..."
    python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0 &
    SSH_GATEWAY_PID=$!
    sleep 2
    if kill -0 $SSH_GATEWAY_PID 2>/dev/null; then
        echo_success "SSH gateway started (PID: $SSH_GATEWAY_PID)"
    else
        echo_warning "SSH gateway failed to start - workspace SSH access may be unavailable"
    fi
else
    echo_info "Skipping SSH gateway (celery worker)"
fi

# ============================================
# Start Application
# ============================================
echo -e "🚀 Starting production server..."
exec "$@"

# EOF
