#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-05 19:08:34 (ywatanabe)"
# File: ./deployment/docker/docker_dev/entrypoint.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

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
# Install SciTeX in Editable Mode (Optional)
# ============================================
try_scitex_installation_in_editable_mode() {
    if [ -d "/scitex-code" ]; then
        # Check if scitex-code is a valid Python project
        if [ -f "/scitex-code/pyproject.toml" ] || [ -f "/scitex-code/setup.py" ]; then
            # Check if scitex is already installed in editable mode from /scitex-code
            if pip show -f scitex 2> /dev/null | grep -q "/scitex-code"; then
                echo -e "${GREEN}✅ Scitex already installed in editable mode${NC}"
            else
                echo_info "Installing scitex (editable mode)..."

                uv pip install -e "/scitex-code[dl,ml,jupyter,neuro,web,scholar,writer,dev]" --link-mode=copy > /dev/null
            fi
            verify_scitex_package
        else
            echo -e "⚠️  WARNING: /scitex-code exists but is not a valid Python package"
            echo -e "   (missing pyproject.toml or setup.py at root)"
            echo -e "   Skipping scitex package installation..."
        fi
    else
        echo -e "⚠️  WARNING: /scitex-code not mounted!"
        echo -e "   Skipping scitex package installation..."
    fi
}
try_scitex_installation_in_editable_mode

add_insufficient_python_packages() {
    pip install pygments > /dev/null 2>&1 || true
}
add_insufficient_python_packages

# ============================================
# Vite Dev Server (HMR - Hot Module Replacement)
# ============================================
# Vite serves TypeScript directly and provides HMR for instant updates
start_vite_dev_server() {
    if [ -f "/app/package.json" ] && [ -f "/app/vite.config.ts" ]; then
        # Check if Vite is already running
        if pgrep -f "vite" > /dev/null 2>&1; then
            echo_info "Vite dev server already running"
            return 0
        fi

        echo_info "Starting Vite dev server (HMR)..."
        cd /app || return 0

        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            echo_warning "Installing Node dependencies..."
            npm install --silent 2>&1 | grep -v "npm WARN" || true
        fi

        # Start Vite dev server in background
        nohup npm run dev \
            > /app/logs/vite-dev.log 2>&1 &
        VITE_PID=$!
        echo_success "Vite dev server started (PID: $VITE_PID)"
        echo "   URL: http://127.0.0.1:5173"
        echo "   HMR: Enabled (instant module updates)"
        echo "   Log: tail -f /app/logs/vite-dev.log"

        cd /app || return 0
    else
        echo_warning "Vite config not found - using TypeScript watch fallback"
        # Fall back to TypeScript watch mode
        start_typescript_build_watcher_fallback
    fi
}

# ============================================
# TypeScript Watch Mode (Fallback when Vite not available)
# ============================================
start_typescript_build_watcher_fallback() {
    if [ -d "/app/tsconfig" ] && [ -f "/app/tsconfig/package.json" ]; then
        # Check if tsc is already running
        if pgrep -f "tsc.*--watch" > /dev/null 2>&1; then
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
            > /app/logs/tsc-watch-all.log 2>&1 &
        TSC_ALL_PID=$!
        echo_success "TypeScript watch (ALL apps) started (PID: $TSC_ALL_PID)"
        echo -e "   Watching: static/ts/**, apps/*/static/*/ts/**"
        echo -e "   Log: tail -f /app/logs/tsc-watch-all.log"

        cd /app || return 0
    else
        echo_warning "/app/tsconfig not found - skipping TypeScript watch mode"
    fi
}

# Start Vite (with fallback to tsc --watch)
start_vite_dev_server

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
else
    # Hot-reload restart - skip migrations
    echo_info "Hot-reload restart detected - skipping migrations"
    wait_for_database  # Still wait for DB to be ready
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
# Template Hot Reload
# ============================================
# Note: Template hot reload is handled by django-browser-reload via Django's autoreload
# No separate watcher needed - visitor pool init is now optimized with fast-path

# ============================================
# Start Background Services (First Start Only)
# ============================================
# Background services persist across hot-reload restarts
if [ ! -f "$MIGRATION_SENTINEL" ]; then
    # Start SSH Gateway (Background)
    start_ssh_gateway() {
        echo_info "Starting SSH gateway on port 2200..."
        nohup python manage.py run_ssh_gateway \
            --port 2200 \
            --host 0.0.0.0 \
            > /app/logs/ssh-gateway.log 2>&1 &
        SSH_GATEWAY_PID=$!
        echo_success "SSH gateway started (PID: $SSH_GATEWAY_PID)"
        echo -e "   Port: 2200"
        echo -e "   Log: tail -f /app/logs/ssh-gateway.log"
    }
    start_ssh_gateway

    # Start Gitea Auto-Sync Daemon (Background)
    start_gitea_auto_sync() {
        echo_info "Starting Gitea auto-sync daemon (interval: 15 min)..."
        nohup python manage.py auto_sync_workspaces \
            --daemon \
            --interval 900 \
            > /app/logs/auto-sync.log 2>&1 &
        AUTO_SYNC_PID=$!
        echo_success "Auto-sync daemon started (PID: $AUTO_SYNC_PID)"
        echo -e "   Interval: 15 minutes (900s)"
        echo -e "   Log: tail -f /app/logs/auto-sync.log"
    }
    start_gitea_auto_sync
else
    echo_info "Hot-reload restart - background services already running"
fi

# ============================================
# Start Application
# ============================================
echo -e "🚀 Starting development server..."
exec "$@"

# EOF
