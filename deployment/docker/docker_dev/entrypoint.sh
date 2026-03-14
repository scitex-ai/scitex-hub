#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-05 19:08:34 (ywatanabe)"
# File: ./deployment/docker/docker_dev/entrypoint.sh

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PATH="$THIS_DIR/.$(basename "$0").log"
echo -e >"$LOG_PATH"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

set -e

# ============================================
# Development Environment Entry point
# ============================================

# Source common libraries
source /app/deployment/docker/common/lib/logging.src
source /app/deployment/docker/common/lib/database.src
source /app/deployment/docker/common/lib/django.src
source /app/deployment/docker/common/lib/scitex.src
source /app/deployment/docker/common/lib/slurm.src

MIGRATION_SENTINEL="/app/logs/.migrations_done"

if [ -f "$MIGRATION_SENTINEL" ]; then
    echo -e "🔄 Hot-Reload Restart (fast path)"
else
    echo -e "🔧 Development Environment (first start)"
fi

# ============================================
# Sync SLURM UID with Host (Required for Terminal)
# ============================================
sync_slurm_uid || echo_warning "SLURM UID sync skipped - terminal may have issues"

# ============================================
# Clean SLURM State (Prevent Stuck Nodes)
# ============================================
# Cancel stuck COMPLETING jobs and reset node state from previous runs
if command -v scancel &>/dev/null; then
    scancel --state=COMPLETING 2>/dev/null || true
    for node in $(sinfo -h -o"%N" 2>/dev/null); do
        scontrol update NodeName="$node" State=resume 2>/dev/null || true
    done
    echo_success "SLURM state cleaned"
fi

# ============================================
# Install SciTeX + Ecosystem Packages (Editable Mode)
# ============================================
source "$(dirname "$0")/install_ecosystem.sh"

# ============================================
# Pre-generate Matplotlib Font Cache (Runtime - First Start Only)
# ============================================
# Generate font cache after scitex is installed to avoid 10+ minute startup delay
# This only runs once - cache persists in container filesystem
generate_matplotlib_font_cache() {
    local cache_marker="/root/.cache/matplotlib/.fontcache_generated"

    if [ -f "$cache_marker" ]; then
        echo_info "Matplotlib font cache already generated"
        return 0
    fi

    echo_info "Generating matplotlib font cache (one-time, ~30 seconds)..."
    python -c "
import os
os.environ['MPLBACKEND'] = 'Agg'
try:
    import matplotlib.pyplot as plt
    plt.figure()
    print('Font cache generated successfully')
except Exception as e:
    print(f'Font cache generation failed: {e}')
" 2>&1 | grep -v "WARN\|building the font cache" || true

    # Mark as generated
    mkdir -p "$(dirname "$cache_marker")"
    touch "$cache_marker"
    echo_success "Matplotlib font cache ready"
}

# Only run on first start (not on hot-reload restarts)
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    generate_matplotlib_font_cache
else
    echo_info "Hot-reload restart - matplotlib cache already generated"
fi

# ============================================
# Vite Dev Server — All-in-Container
# ============================================
# Platform Vite (port 5173): serves all platform TypeScript
# Dev App Vite (port 5174): serves dev app TypeScript (if any)

start_platform_vite() {
    cd /app || return 0

    # Ensure node_modules exists
    if [ ! -d "node_modules" ]; then
        echo_warning "Installing Node dependencies..."
        npm install --silent 2>&1 | grep -v "npm WARN" || true
    fi

    # Check if platform Vite is already running
    if pgrep -f "vite.*5173" >/dev/null 2>&1; then
        echo_info "Platform Vite already running on port 5173"
        return 0
    fi

    # Clean stale .vite cache (may have wrong ownership from previous runs)
    rm -rf /app/node_modules/.vite/deps 2>/dev/null || true

    echo_info "Starting platform Vite (port 5173, in container)..."

    nohup bash -c '
        while true; do
            echo "[$(date)] Platform Vite starting on port 5173..." >> /app/logs/vite-platform.log
            npx vite >> /app/logs/vite-platform.log 2>&1
            EXIT_CODE=$?
            echo "[$(date)] Platform Vite exited (code $EXIT_CODE), restarting in 3s..." >> /app/logs/vite-platform.log
            sleep 3
        done
    ' >/dev/null 2>&1 &
    VITE_PLATFORM_PID=$!
    echo_success "Platform Vite started (PID: $VITE_PLATFORM_PID)"
    echo "   URL: http://127.0.0.1:5173"
    echo "   Log: tail -f /app/logs/vite-platform.log"
}

start_devapp_vite() {
    cd /app || return 0

    # Check if any dev apps have TypeScript files
    DEV_APP_TS=$(find /app/data/users/*/proj/*/static -name '*.ts' 2>/dev/null | head -1)

    if [ -z "$DEV_APP_TS" ]; then
        echo_info "No dev app TypeScript found — skipping dev app Vite"
        return 0
    fi

    # Check if dev app Vite is already running
    if pgrep -f "vite.*config.*devapp" >/dev/null 2>&1; then
        echo_info "Dev app Vite already running on port 5174"
        return 0
    fi

    echo_info "Starting dev app Vite (port 5174, dev apps only)..."

    nohup bash -c '
        while true; do
            echo "[$(date)] Dev app Vite starting on port 5174..." >> /app/logs/vite-app.log
            npx vite --config vite.config.devapp.ts >> /app/logs/vite-app.log 2>&1
            EXIT_CODE=$?
            echo "[$(date)] Dev app Vite exited (code $EXIT_CODE), restarting in 3s..." >> /app/logs/vite-app.log
            sleep 3
        done
    ' >/dev/null 2>&1 &
    VITE_PID=$!
    echo_success "Dev app Vite started (PID: $VITE_PID)"
    echo "   URL: http://127.0.0.1:5174"
    echo "   Scope: Dev app TypeScript only"
    echo "   Log: tail -f /app/logs/vite-app.log"
}

# ============================================
# TypeScript Watch Mode (Fallback when Vite not available)
# ============================================
start_typescript_build_watcher_fallback() {
    if [ -d "/app/tsconfig" ] && [ -f "/app/tsconfig/package.json" ]; then
        # Check if tsc is already running
        if pgrep -f "tsc.*--watch" >/dev/null 2>&1; then
            echo_info "TypeScript watcher already running"
            return 0
        fi

        echo_info "Starting TypeScript watch mode for ALL apps..."
        cd /app/tsconfig || return 0

        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            echo_warning "Installing Node dependencies..."
            npm install --silent 2>&1 | grep -v "npm WARN" || true
        fi

        # Start unified TypeScript compiler in watch mode for ALL apps (background)
        nohup npm run build:all:watch \
            >/app/logs/tsc-watch-all.log 2>&1 &
        TSC_ALL_PID=$!
        echo_success "TypeScript watch (ALL apps) started (PID: $TSC_ALL_PID)"
        echo -e "   Watching: static/ts/**, apps/*/static/*/ts/**"
        echo -e "   Log: tail -f /app/logs/tsc-watch-all.log"

        cd /app || return 0
    else
        echo_warning "/app/tsconfig not found - skipping TypeScript watch mode"
    fi
}

# Only start web-related services for the Django container (not celery/flower)
# Check if the command ($@) is the Django runserver
IS_DJANGO_CONTAINER=false
for arg in "$@"; do
    if [ "$arg" = "runserver" ]; then
        IS_DJANGO_CONTAINER=true
        break
    fi
done

if [ "$IS_DJANGO_CONTAINER" = true ]; then
    # Start Vite servers (platform + dev app)
    start_platform_vite
    start_devapp_vite
else
    echo_info "Non-Django container - skipping Vite dev server"
fi

# ============================================
# Database & Django Setup
# ============================================
# Skip migrations on hot-reload restarts (only run on first container start)
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    # First container start - run full setup
    wait_for_database
    run_migrations
    # collect_static_files  # Not needed in development - Django serves static files from app directories

    # Mark migrations as done (persists in /app/logs volume)
    touch "$MIGRATION_SENTINEL"

    # Sync Unix user accounts (Linux UID isolation)
    echo_info "Syncing Unix user accounts (UID isolation)..."
    python manage.py sync_unix_users 2>&1 | grep -v "ERRO\|WARN" || true
    echo_success "Unix user accounts synced"
else
    # Hot-reload restart - skip migrations
    echo_info "Hot-reload restart detected - skipping migrations"
    wait_for_database # Still wait for DB to be ready
fi

# ============================================
# Initialize Visitor Pool
# ============================================
# Only run on first start (fast-path check handles restarts gracefully)
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    initialize_visitor_pool() {
        echo_info "Initializing visitor pool..."
        python manage.py create_visitor_pool --verbosity 0 2>&1 | grep -v "ERRO\|WARN" || true
        echo_success "Visitor pool ready"
    }
    initialize_visitor_pool
else
    echo_info "Hot-reload restart - visitor pool already initialized"
fi

# ============================================
# Initialize Test User (Development Only - First Start Only)
# ============================================
# Create test-user for development and E2E testing
initialize_test_user() {
    local username="${SCITEX_CLOUD_TEST_USER_USERNAME:-test-user}"
    local password="${SCITEX_CLOUD_TEST_USER_PASSWORD:-Password123!}"
    local email="test@example.com"

    echo_info "Ensuring test user exists: $username"
    python manage.py init_test_user \
        --username="$username" \
        --email="$email" \
        --password="$password" \
        2>&1 | grep -v "ERRO\|WARN" || true
    echo_success "Test user ready: $username"
}
# Only run on first start (not on hot-reload restarts)
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    initialize_test_user
else
    echo_info "Hot-reload restart - test user already initialized"
fi

# ============================================
# Generate Plot Gallery to Static Directory
# ============================================
# Generate scitex.plt gallery examples into static/shared/images/gallery
# This makes thumbnails available as static files (no API needed)
generate_static_gallery() {
    local gallery_path="/app/static/shared/images/gallery"

    # Check if gallery already exists (fast-path)
    if [ -d "$gallery_path" ] && [ "$(find "$gallery_path" -name '*.png' 2>/dev/null | head -1)" ]; then
        echo_info "Static gallery already exists, skipping generation"
        return 0
    fi

    echo_info "Generating plot gallery to static directory..."
    python -c "
import os
os.environ['MPLBACKEND'] = 'Agg'
try:
    import scitex as stx
    result = stx.plt.gallery.generate(
        output_dir='$gallery_path',
        figsize=(4, 3),
        dpi=150,
        save_csv=True,
        save_png=True,
        verbose=False
    )
    png_count = len(result.get('png', []))
    csv_count = len(result.get('csv', []))
    print(f'Generated {png_count} PNG, {csv_count} CSV to static gallery')
except Exception as e:
    print(f'Gallery generation failed: {e}')
" 2>&1 | grep -v "ERRO\|WARN" || true
    echo_success "Static gallery ready"
}

# Run on first start only
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    generate_static_gallery
fi

# ============================================
# Template Hot Reload
# ============================================
# Note: Template hot reload is handled by django-browser-reload via Django's autoreload
# No separate watcher needed - visitor pool init is now optimized with fast-path

# ============================================
# Start Background Services (if not already running)
# ============================================
# Check if process is running by checking port or process name

# Start Terminal Broker (Background) - handles PTY operations safely
# The terminal broker runs pty.fork() in a separate process from Daphne,
# preventing asyncio/signal conflicts that can cause deadlocks.
start_terminal_broker_if_needed() {
    local socket_path="/tmp/scitex-terminal-broker.sock"
    if [ ! -S "$socket_path" ]; then
        echo_info "Starting terminal broker..."
        nohup python manage.py run_terminal_broker \
            >/app/logs/terminal-broker.log 2>&1 &
        TERMINAL_BROKER_PID=$!
        sleep 1 # Give it a moment to start
        if [ -S "$socket_path" ]; then
            echo_success "Terminal broker started (PID: $TERMINAL_BROKER_PID)"
            echo -e "   Socket: $socket_path"
            echo -e "   Log: tail -f /app/logs/terminal-broker.log"
        else
            echo_warning "Terminal broker may have failed - terminals will use fallback mode"
        fi
    else
        echo_success "Terminal broker already running"
    fi
}
# Start SSH Gateway (Background) - check if port 2200 is in use
start_ssh_gateway_if_needed() {
    if ! nc -z 127.0.0.1 2200 2>/dev/null; then
        echo_info "Starting SSH gateway on port 2200..."
        nohup python manage.py run_ssh_gateway \
            --port 2200 \
            --host 0.0.0.0 \
            >/app/logs/ssh-gateway.log 2>&1 &
        SSH_GATEWAY_PID=$!
        sleep 1 # Give it a moment to start
        if nc -z 127.0.0.1 2200 2>/dev/null; then
            echo_success "SSH gateway started (PID: $SSH_GATEWAY_PID)"
            echo -e "   Port: 2200"
            echo -e "   Log: tail -f /app/logs/ssh-gateway.log"
        else
            echo -e "${YELLOW}⚠️  SSH gateway may have failed to start - check logs${NC}"
        fi
    else
        echo_success "SSH gateway already running on port 2200"
    fi
}
# Start Gitea Auto-Sync Daemon (Background) - check if process exists
start_gitea_auto_sync_if_needed() {
    if ! pgrep -f "auto_sync_workspaces" >/dev/null 2>&1; then
        echo_info "Starting Gitea auto-sync daemon (interval: 15 min)..."
        nohup python manage.py auto_sync_workspaces \
            --daemon \
            --interval 900 \
            >/app/logs/auto-sync.log 2>&1 &
        AUTO_SYNC_PID=$!
        echo_success "Auto-sync daemon started (PID: $AUTO_SYNC_PID)"
        echo -e "   Interval: 15 minutes (900s)"
        echo -e "   Log: tail -f /app/logs/auto-sync.log"
    else
        echo_success "Gitea auto-sync daemon already running"
    fi
}
# Django-only: terminal broker, SSH gateway, auto-sync (skip for celery/flower)
if [ "$IS_DJANGO_CONTAINER" = true ]; then
    start_terminal_broker_if_needed
    start_ssh_gateway_if_needed
    start_gitea_auto_sync_if_needed
else
    echo_info "Non-Django container - skipping background services"
fi
# ============================================
# Start Application
# ============================================
echo -e "🚀 Starting development server..."
exec "$@"

# EOF
