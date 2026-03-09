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

echo -e "🏭 Production Environment"

# ============================================
# Set BUILD_ID for CSS/JS cache busting
# ============================================
BUILD_ID=$(git -C /app rev-parse --short HEAD 2>/dev/null || date +%s)
export BUILD_ID

# ============================================
# Sync SLURM UID with Host (Required for Terminal)
# ============================================
sync_slurm_uid || echo_warning "SLURM UID sync skipped - terminal may have issues"

# ============================================
# Verify SciTeX from PyPI
# ============================================
verify_scitex_package

# ============================================
# TEMPORARY FIX: Upgrade scitex-writer to 2.6.5+
# Needed because Docker layer cache has older version
# TODO: Remove after next full rebuild with --no-cache
# ============================================
echo_info "Upgrading scitex-writer (temporary fix for scripts directory)..."
pip install --quiet --upgrade "scitex-writer>=2.6.5" 2>/dev/null || true
echo_success "scitex-writer upgraded"

# Ensure we're NOT using editable install
if [ -d "/scitex-code" ]; then
    echo -e "⚠️  WARNING: /scitex-code detected in production!"
    echo -e "   This should not be mounted in production environments."
    echo -e "   Using PyPI version anyway..."
fi

# ============================================
# Database & Django Setup
# ============================================
wait_for_database
run_migrations
collect_static_files

# ============================================
# Clear Template Cache (ensure fresh templates)
# ============================================
echo_info "Clearing template cache..."
rm -rf /home/scitex/.scitex/templates/ 2>/dev/null || true
echo_success "Template cache cleared"

# ============================================
# Initialize Visitor Pool
# ============================================
echo_info "Initializing visitor pool..."
python manage.py create_visitor_pool --verbosity 0 2>&1 | grep -v "ERRO\|WARN" || true
echo_success "Visitor pool ready"

# ============================================
# Conditional NPM Install & TypeScript Build
# ============================================
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.install-timestamp" ]; then
    echo_info "Installing npm dependencies (including dev for Vite build)..."
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
fi

if [ "$VITE_REBUILD_NEEDED" = true ]; then
    # Ensure vite output dir is writable (collectstatic or prior build may leave root-owned files)
    if [ -d "staticfiles/vite" ]; then
        chmod -R u+rwX staticfiles/vite 2>/dev/null || true
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
# Dev App Vite Server (On-Demand)
# ============================================
# Container Vite for developmentally-installed app TypeScript
# Platform TS is pre-built above; this serves live TS for user-installed dev apps
start_dev_app_vite() {
    local DEV_APP_TS
    DEV_APP_TS=$(find /app/data/users/*/proj/*/static -name '*.ts' 2>/dev/null | head -1)

    if [ -z "$DEV_APP_TS" ]; then
        echo_info "No dev app TypeScript found — skipping dev app Vite"
        return 0
    fi

    if pgrep -f "vite.*config.*devapp" >/dev/null 2>&1; then
        echo_info "Dev app Vite already running"
        return 0
    fi

    echo_info "Starting dev app Vite (port 5174, dev apps only)..."
    nohup bash -c '
        while true; do
            echo "[$(date)] Dev app Vite starting on port 5174..." >> /app/logs/vite-devapp.log
            npx vite --config vite.config.devapp.ts >> /app/logs/vite-devapp.log 2>&1
            EXIT_CODE=$?
            echo "[$(date)] Dev app Vite exited (code $EXIT_CODE), restarting in 3s..." >> /app/logs/vite-devapp.log
            sleep 3
        done
    ' >/dev/null 2>&1 &
    echo_success "Dev app Vite started (PID: $!)"
}

# Only start for Django container, not celery
if [[ ! "$*" =~ "celery" ]]; then
    start_dev_app_vite
fi

# ============================================
# Start Terminal Broker (Background) - Required for PTY operations
# ============================================
# The terminal broker handles pty.fork() in a separate process from Daphne.
# This prevents asyncio/signal conflicts that can cause deadlocks.
# Skip for celery workers - they don't handle terminal WebSockets
if [[ ! "$*" =~ "celery" ]]; then
    echo_info "Starting terminal broker..."
    python manage.py run_terminal_broker &
    TERMINAL_BROKER_PID=$!
    sleep 1
    if kill -0 $TERMINAL_BROKER_PID 2>/dev/null; then
        echo_success "Terminal broker started (PID: $TERMINAL_BROKER_PID)"
    else
        echo_warning "Terminal broker failed to start - terminals will use fallback mode"
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
