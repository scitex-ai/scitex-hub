#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-05-22 04:47:00 (ywatanabe)"
# File: ./scripts/deploy_prod.sh

# SciTeX Cloud Production Deployment Script
# Based on best practices from airight project

set -e # Exit on any error

APP_HOME="/home/ywatanabe/proj/scitex-cloud"
LOG_DIR="/var/log/uwsgi"
RUN_DIR="/run"
PYTHON_BIN="$APP_HOME/.venv/bin/python"
MANAGE_PY="$PYTHON_BIN $APP_HOME/manage.py"

# ANSI colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    echo "SciTeX Cloud Production Deployment"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --deploy       Full deployment (setup, migrate, static, start)"
    echo "  -i, --install      Setup systemd services and Nginx (first time only)"
    echo "  -m, --migrate      Run database migrations only"
    echo "  -s, --static       Collect static files only"
    echo "  -r, --restart      Restart services only"
    echo "  -c, --check        Check system configuration"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -d              # Full deployment (includes setup)"
    echo "  $0 -i              # First-time setup only"
    echo "  $0 -m -s           # Migrate and collect static"
    echo "  $0 -r              # Restart services"
    exit 1
}

check_dependencies() {
    echo_info "Checking dependencies..."

    # Check if virtual environment exists
    if [ ! -d "$APP_HOME/.venv" ]; then
        echo_error "Virtual environment not found at $APP_HOME/.venv"
        exit 1
    fi

    # Check if Python executable exists
    if [ ! -f "$PYTHON_BIN" ]; then
        echo_error "Python executable not found at $PYTHON_BIN"
        exit 1
    fi

    # Check if manage.py exists
    if [ ! -f "$APP_HOME/manage.py" ]; then
        echo_error "Django manage.py not found at $APP_HOME/manage.py"
        exit 1
    fi

    echo_success "Dependencies check passed"
}

create_directories() {
    echo_info "Creating required directories..."

    # Create log directory
    sudo mkdir -p "$LOG_DIR" || echo_warning "Could not create $LOG_DIR"
    sudo chown -R www-data:www-data "$LOG_DIR" 2> /dev/null || echo_warning "Could not set ownership for $LOG_DIR"

    # Create run directory for PID files and sockets
    sudo mkdir -p "$RUN_DIR" || echo_warning "Could not create $RUN_DIR"
    sudo chown -R www-data:www-data "$RUN_DIR" 2> /dev/null || echo_warning "Could not set ownership for $RUN_DIR"

    echo_success "Directories created"
}

run_migrations() {
    echo_info "Running database migrations..."

    cd "$APP_HOME"
    source .venv/bin/activate

    # Set production environment
    export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_prod

    echo_info "Making migrations..."
    $MANAGE_PY makemigrations --settings=config.settings.settings_prod

    echo_info "Applying migrations..."
    $MANAGE_PY migrate --settings=config.settings.settings_prod

    echo_success "Database migrations completed"
}

collect_static() {
    echo_info "Collecting static files..."

    cd "$APP_HOME"
    source .venv/bin/activate

    # Set production environment
    export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_prod

    # Collect new static files
    $MANAGE_PY collectstatic --noinput --settings=config.settings.settings_prod

    echo_success "Static files collected"
}

stop_services() {
    echo_info "Stopping services..."

    # Stop uWSGI systemd service
    sudo systemctl stop scitex_cloud_prod 2> /dev/null || echo_warning "scitex_cloud_prod service not running"

    # Stop any remaining uWSGI processes
    sudo pkill -f uwsgi 2> /dev/null || echo_warning "No additional uWSGI processes to stop"

    # Remove socket files
    sudo rm -f "$RUN_DIR/scitex_cloud.sock" 2> /dev/null || true

    echo_success "Services stopped"
}

start_services() {
    echo_info "Starting services..."

    # Start uWSGI via systemd
    echo_info "Starting uWSGI service (scitex_cloud_prod)..."
    sudo systemctl start scitex_cloud_prod

    # Wait a moment for uWSGI to start
    sleep 3

    # Check if uWSGI service is running
    if sudo systemctl is-active --quiet scitex_cloud_prod; then
        echo_success "uWSGI service started successfully"
    else
        echo_error "Failed to start uWSGI service"
        echo_info "Check logs: sudo journalctl -u scitex_cloud_prod -n 50"
        exit 1
    fi

    # Check if socket was created
    if [ -S "$RUN_DIR/scitex_cloud.sock" ]; then
        echo_success "Socket created: $RUN_DIR/scitex_cloud.sock"
    else
        echo_warning "Socket not found at $RUN_DIR/scitex_cloud.sock"
    fi

    # Restart Nginx
    echo_info "Restarting Nginx..."
    sudo systemctl restart nginx 2> /dev/null || echo_warning "Could not restart Nginx"

    if sudo systemctl is-active --quiet nginx; then
        echo_success "Nginx is running"
    else
        echo_warning "Nginx may not be running properly"
    fi

    echo_success "Services started"
}

run_checks() {
    echo_info "Running system checks..."

    cd "$APP_HOME"
    source .venv/bin/activate

    # Set production environment
    export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_prod

    # Run Django system checks
    echo_info "Running Django system checks..."
    $MANAGE_PY check --deploy --settings=config.settings.settings_prod

    # Test database connection
    echo_info "Testing database connection..."
    $MANAGE_PY shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection: OK')" --settings=config.settings.settings_prod

    echo_success "System checks passed"
}

setup_systemd() {
    echo_info "Setting up systemd services and Nginx..."

    # Copy uWSGI systemd service file
    echo_info "Installing uWSGI systemd service..."
    sudo cp "$APP_HOME/deployment/uwsgi/scitex_cloud_prod.service" /etc/systemd/system/scitex_cloud_prod.service
    sudo systemctl daemon-reload
    sudo systemctl enable scitex_cloud_prod
    echo_success "uWSGI service installed"

    # Copy Nginx configuration
    echo_info "Installing Nginx configuration..."
    sudo cp "$APP_HOME/deployment/nginx/scitex_cloud_prod.conf" /etc/nginx/sites-available/scitex_cloud
    sudo ln -sf /etc/nginx/sites-available/scitex_cloud /etc/nginx/sites-enabled/scitex_cloud

    # Test Nginx configuration
    echo_info "Testing Nginx configuration..."
    sudo nginx -t

    sudo systemctl enable nginx
    echo_success "Nginx configuration installed"

    echo_success "Systemd services and Nginx setup completed"
}

# Parse command line arguments
DO_MIGRATE=false
DO_STATIC=false
DO_RESTART=false
DO_DEPLOY=false
DO_CHECK=false
DO_INSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d | --deploy)
            DO_DEPLOY=true
            DO_INSTALL=true
            DO_MIGRATE=true
            DO_STATIC=true
            DO_RESTART=true
            shift
            ;;
        -i | --install)
            DO_INSTALL=true
            shift
            ;;
        -m | --migrate)
            DO_MIGRATE=true
            shift
            ;;
        -s | --static)
            DO_STATIC=true
            shift
            ;;
        -r | --restart)
            DO_RESTART=true
            shift
            ;;
        -c | --check)
            DO_CHECK=true
            shift
            ;;
        -h | --help)
            usage
            ;;
        *)
            echo_error "Unknown option: $1"
            usage
            ;;
    esac
done

# If no options provided, show usage
if [ "$DO_MIGRATE" = false ] && [ "$DO_STATIC" = false ] && [ "$DO_RESTART" = false ] && [ "$DO_DEPLOY" = false ] && [ "$DO_CHECK" = false ] && [ "$DO_INSTALL" = false ]; then
    usage
fi

# Main execution
echo_info "Starting SciTeX Cloud production deployment..."

check_dependencies
create_directories

if [ "$DO_INSTALL" = true ]; then
    setup_systemd
fi

if [ "$DO_CHECK" = true ]; then
    run_checks
fi

if [ "$DO_MIGRATE" = true ]; then
    run_migrations
fi

if [ "$DO_STATIC" = true ]; then
    collect_static
fi

if [ "$DO_RESTART" = true ]; then
    stop_services
    start_services
fi

echo_success "Deployment completed successfully!"

if [ "$DO_DEPLOY" = true ]; then
    echo_info "=== Deployment Summary ==="
    echo_info "- Systemd services: Installed and enabled"
    echo_info "- Database migrations: Applied"
    echo_info "- Static files: Collected"
    echo_info "- Services: Restarted"
    echo_info "- Logs: $LOG_DIR"
    echo_info "=========================="
fi
