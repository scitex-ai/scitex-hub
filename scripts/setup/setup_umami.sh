#!/bin/bash
# Timestamp: 2026-01-29
# Author: ywatanabe
# File: scripts/setup/setup_umami.sh
# Description: Automated Umami analytics setup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Determine environment
ENV="${1:-dev}"
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    log_error "Usage: $0 [dev|prod]"
    exit 1
fi

ENV_FILE="$PROJECT_ROOT/deployment/docker/envs/.env.$ENV"
COMPOSE_DIR="$PROJECT_ROOT/deployment/docker/docker_$ENV"

log_info "Setting up Umami for environment: $ENV"

# Check if docker is running
if ! docker info &>/dev/null; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Get container names based on environment
POSTGRES_CONTAINER="scitex-hub-${ENV}-postgres-1"
UMAMI_CONTAINER="scitex-hub-${ENV}-umami-1"

# Step 1: Create umami database if it doesn't exist
log_info "Checking umami database..."

# PostgreSQL user and default database
PG_USER="scitex_${ENV}"
PG_DB="scitex_hub_${ENV}"

if docker exec "$POSTGRES_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -lqt | cut -d \| -f 1 | grep -qw umami; then
    log_success "Database 'umami' already exists"
else
    log_info "Creating 'umami' database..."
    docker exec "$POSTGRES_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "CREATE DATABASE umami;" || {
        log_error "Failed to create database. Is PostgreSQL running?"
        log_error "Try: make env=$ENV start"
        exit 1
    }
    log_success "Database 'umami' created"
fi

# Step 2: Ensure Umami container is running
log_info "Checking Umami container..."
if docker ps --format '{{.Names}}' | grep -q "$UMAMI_CONTAINER"; then
    log_success "Umami container is running"
else
    log_info "Starting Umami container..."
    cd "$COMPOSE_DIR"
    docker compose up -d umami

    # Wait for Umami to be healthy
    log_info "Waiting for Umami to be ready..."
    for _ in {1..30}; do
        if curl -s "http://127.0.0.1:3300/api/heartbeat" &>/dev/null; then
            log_success "Umami is ready"
            break
        fi
        sleep 2
    done
fi

# Step 3: Check if website ID is configured
WEBSITE_ID=$(grep -E "^SCITEX_CLOUD_UMAMI_WEBSITE_ID=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")

if [[ -z "$WEBSITE_ID" ]]; then
    log_warn "Umami Website ID not configured yet."
    echo ""
    echo -e "${YELLOW}=== Manual Step Required ===${NC}"
    echo "1. Open Umami: http://127.0.0.1:3300"
    echo "2. Login with: admin / umami"
    echo "3. Change the default password"
    echo "4. Go to Settings → Websites → Add website"
    echo "   - Name: SciTeX $ENV"
    echo "   - Domain: $(grep SCITEX_CLOUD_DOMAIN "$ENV_FILE" | cut -d= -f2 || echo '127.0.0.1')"
    echo "5. Copy the Website ID and run:"
    echo ""
    echo -e "   ${GREEN}$0 $ENV --set-website-id <YOUR_WEBSITE_ID>${NC}"
    echo ""
else
    log_success "Website ID configured: $WEBSITE_ID"
fi

# Handle --set-website-id flag
if [[ "${2:-}" == "--set-website-id" && -n "${3:-}" ]]; then
    NEW_WEBSITE_ID="$3"
    log_info "Setting Website ID: $NEW_WEBSITE_ID"

    if grep -q "^SCITEX_CLOUD_UMAMI_WEBSITE_ID=" "$ENV_FILE"; then
        sed -i "s|^SCITEX_CLOUD_UMAMI_WEBSITE_ID=.*|SCITEX_CLOUD_UMAMI_WEBSITE_ID=$NEW_WEBSITE_ID|" "$ENV_FILE"
    else
        echo "SCITEX_CLOUD_UMAMI_WEBSITE_ID=$NEW_WEBSITE_ID" >>"$ENV_FILE"
    fi

    log_success "Website ID saved to $ENV_FILE"
    log_info "Restart Django to apply: make env=$ENV restart"
fi

# Show status
echo ""
log_info "Umami Status:"
echo "  Dashboard: http://127.0.0.1:3300"
echo "  Script URL: http://127.0.0.1:3300/script.js"
echo "  Website ID: ${WEBSITE_ID:-<not configured>}"
