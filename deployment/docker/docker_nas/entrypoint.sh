#!/bin/bash
set -e

# ============================================
# Production/NAS Environment Entrypoint
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
collect_static_files

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
# Check if build is needed by comparing source files vs build output
if [ ! -d "staticfiles/vite" ] || [ "vite.config.ts" -nt "staticfiles/vite/.build-timestamp" ]; then
    echo_info "Building TypeScript files with Vite..."
    npm run build
    touch staticfiles/vite/.build-timestamp
    echo_success "TypeScript build complete"
else
    echo_info "TypeScript build already up to date"
fi

# ============================================
# Start SSH Gateway (Background)
# ============================================
echo_info "Starting SSH gateway on port 2200..."
python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0 &
SSH_GATEWAY_PID=$!
sleep 2
if kill -0 $SSH_GATEWAY_PID 2>/dev/null; then
    echo_success "SSH gateway started (PID: $SSH_GATEWAY_PID)"
else
    echo_warning "SSH gateway failed to start - workspace SSH access may be unavailable"
fi

# ============================================
# Start Application
# ============================================
echo -e "🚀 Starting production server..."
exec "$@"

# EOF
