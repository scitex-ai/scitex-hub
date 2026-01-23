#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 12:51:58 (ywatanabe)"
# File: ./server.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

BLACK='\033[0;30m'
LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
# ---------------------------------------

# ----------------------------------------
# SciTeX Cloud Server Management Script
# Following AIRight's best practices for server management

# Script directory - resolve symlinks to get actual location
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$SCRIPT_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
# Go up two levels: scripts/server/ -> scripts/ -> project_root/
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/run"

# Create directories if they don't exist
mkdir -p "$LOG_DIR" "$PID_DIR"

# Color codes for output
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage information
show_usage() {
    cat << EOF
SciTeX Cloud Server Management

Usage: $0 [COMMAND] [OPTIONS]

COMMANDS:
    start       Start the server (default: development mode)
    stop        Stop all SciTeX Cloud processes
    restart     Restart the server
    status      Show server status
    logs        View server logs
    clean       Clean temporary files and caches
    test        Run tests
    shell       Open Django shell
    migrate     Run database migrations
    static      Collect static files

OPTIONS:
    -m, --mode MODE         Server mode: dev, prod, windows (default: dev)
    -p, --port PORT         Port number for dev server (default: 8000)
    -c, --clean             Clean before starting
    -s, --static            Collect static files
    -h, --help              Show this help message

EXAMPLES:
    $0 start                    # Start development server
    $0 start -m prod            # Start production server (systemd uWSGI)
    $0 start -m windows         # Start for Windows access
    $0 stop                     # Stop all servers
    $0 status                   # Check server status
    $0 logs                     # View logs
    $0 test                     # Run tests

EOF
}

# Default values
MODE="dev"
PORT="8000"
DO_CLEAN=false
DO_STATIC=false
COMMAND="start"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        start | stop | restart | status | logs | clean | test | shell | migrate | static)
            COMMAND="$1"
            shift
            ;;
        -m | --mode)
            MODE="$2"
            shift 2
            ;;
        -p | --port)
            PORT="$2"
            shift 2
            ;;
        -c | --clean)
            DO_CLEAN=true
            shift
            ;;
        -s | --static)
            DO_STATIC=true
            shift
            ;;
        -h | --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Activate virtual environment
activate_venv() {
    # Check if already in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        log_info "Using active virtual environment: $VIRTUAL_ENV"
        return 0
    fi

    # Try to find and activate virtual environment
    if [ -d "$PROJECT_ROOT/.env" ]; then
        log_info "Activating virtual environment (.env)..."
        source "$PROJECT_ROOT/.env/bin/activate"
    elif [ -d "$PROJECT_ROOT/env" ]; then
        log_info "Activating virtual environment (env)..."
        source "$PROJECT_ROOT/env/bin/activate"
    elif [ -d "$PROJECT_ROOT/.env-3.11" ]; then
        log_info "Activating Python 3.11 environment..."
        source "$PROJECT_ROOT/.env-3.11/bin/activate"
    else
        log_error "No virtual environment found!"
        log_info "Create one with: python3 -m venv .env"
        exit 1
    fi
}

# Stop server function
stop_server() {
    log_info "Stopping SciTeX Cloud processes..."

    # Stop systemd services if running and kill Django dev server
    if systemctl is-active --quiet scitex_cloud_prod 2> /dev/null; then
        log_info "Stopping systemd uWSGI service..."
        sudo systemctl stop scitex_cloud_prod 2> /dev/null || true
    fi

    # Kill Django development server
    pkill -f "python.*manage.py runserver" 2> /dev/null || true

    log_success "All processes stopped"
}

# Clean temporary files
clean_temp() {
    log_info "Cleaning temporary files..."
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2> /dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2> /dev/null || true
    find "$PROJECT_ROOT" -type f -name ".DS_Store" -delete 2> /dev/null || true
    rm -rf "$PROJECT_ROOT/staticfiles/*" 2> /dev/null || true
    log_success "Cleanup complete"
}

# Run migrations
run_migrations() {
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT"
    python manage.py makemigrations
    python manage.py migrate
    log_success "Migrations complete"
}

# Collect static files
collect_static() {
    log_info "Collecting static files..."
    cd "$PROJECT_ROOT"
    python manage.py collectstatic --noinput
    log_success "Static files collected"
}

# Start development server
start_dev() {
    stop_server

    cd "$PROJECT_ROOT"

    if [[ "$MODE" == "windows" ]]; then
        WSL_IP=$(ip -4 addr show eth0 2> /dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "127.0.0.1")
        log_success "Starting development server for Windows access..."
        log_info ""
        log_info "===================================================="
        log_success "Access from Windows: http://$WSL_IP:$PORT"
        log_info "===================================================="
        log_info ""
    else
        log_success "Starting development server..."
        log_info "Access at: http://localhost:$PORT"
    fi

    log_info "Admin panel: http://localhost:$PORT/admin"
    log_info "Hot reload enabled"
    log_info "Press Ctrl+C to stop"

    python manage.py runserver 0.0.0.0:$PORT
}

# Start production server
start_prod() {
    stop_server

    cd "$PROJECT_ROOT"

    log_info "Starting production server via systemd..."

    # Check if systemd service exists
    if ! systemctl list-unit-files | grep -q scitex_cloud_prod.service; then
        log_error "Systemd service not installed!"
        log_info "Install it with: sudo bash scripts/prod/deploy_prod.sh --install"
        exit 1
    fi

    # Start the service
    sudo systemctl start scitex_cloud_prod

    sleep 2

    # Check if it started successfully
    if systemctl is-active --quiet scitex_cloud_prod; then
        log_success "Production server started successfully"
        log_info ""
        log_info "===================================================="
        log_success "Production server: Nginx + uWSGI (systemd)"
        log_info "Service: scitex_cloud_prod"
        log_info "Socket: $PROJECT_ROOT/run/scitex_cloud.sock"
        log_info "Access via: https://scitex.ai"
        log_info "===================================================="
        log_info ""
        log_info "Commands:"
        log_info "  Check status:  sudo systemctl status scitex_cloud_prod"
        log_info "  View logs:     sudo journalctl -u scitex_cloud_prod -f"
        log_info "  Stop server:   ./server.sh stop"
    else
        log_error "Failed to start production server"
        log_info "Check logs: sudo journalctl -u scitex_cloud_prod -n 50"
        exit 1
    fi
}

# Show server status
show_status() {
    log_info "SciTeX Cloud Server Status"
    echo "============================"

    # Check systemd uWSGI service
    if systemctl is-active --quiet scitex_cloud_prod 2> /dev/null; then
        log_success "Systemd uWSGI service (scitex_cloud_prod): RUNNING"
        systemctl status scitex_cloud_prod --no-pager -l | head -n 15
        echo ""
        log_info "Socket status:"
        ls -l "$PROJECT_ROOT/run/scitex_cloud.sock" 2> /dev/null || log_warning "Socket not found"
    else
        log_warning "Systemd uWSGI service (scitex_cloud_prod): NOT RUNNING"
    fi

    echo ""

    # Check Nginx
    if systemctl is-active --quiet nginx 2> /dev/null; then
        log_success "Nginx: RUNNING"
    else
        log_warning "Nginx: NOT RUNNING"
    fi

    echo ""

    # Check Django dev server
    if pgrep -f "python.*manage.py runserver" > /dev/null; then
        log_success "Django development server: RUNNING"
        ps aux | grep "python.*manage.py runserver" | grep -v grep
    else
        log_warning "Django development server: NOT RUNNING"
    fi
}

# View logs
view_logs() {
    log_info "Viewing SciTeX Cloud logs..."

    # Check if production service is running
    if systemctl is-active --quiet scitex_cloud_prod 2> /dev/null; then
        log_info "Showing systemd uWSGI logs (Ctrl+C to exit)..."
        sudo journalctl -u scitex_cloud_prod -f
    else
        # Use multitail if available
        if command -v multitail &> /dev/null; then
            multitail -f "$LOG_DIR/django.log" \
                -f "$LOG_DIR/app.log" 2> /dev/null \
                || tail -f "$LOG_DIR"/*.log
        else
            # Fall back to regular tail
            tail -f "$LOG_DIR"/*.log
        fi
    fi
}

# Main command execution
case $COMMAND in
    start)
        activate_venv

        # Set environment early based on mode
        case $MODE in
            prod)
                export SCITEX_CLOUD_ENV=production
                if [ -z "$SCITEX_CLOUD_DJANGO_SECRET_KEY" ]; then
                    log_error "SCITEX_CLOUD_DJANGO_SECRET_KEY not set for production!"
                    exit 1
                fi
                ;;
            dev | windows)
                export SCITEX_CLOUD_ENV=development
                export SCITEX_CLOUD_DJANGO_SECRET_KEY="${SCITEX_CLOUD_DJANGO_SECRET_KEY:-dev-secret-key-123}"
                ;;
        esac

        # Clean if requested
        if $DO_CLEAN; then
            clean_temp
        fi

        # Run migrations
        run_migrations

        # For production: collect static, set permissions, and manage services
        if [[ "$MODE" == "prod" ]]; then
            log_info "Preparing production deployment..."

            # Kill any remaining processes (non-sudo)
            pkill -9 -f "uwsgi" 2> /dev/null || true
            pkill -f "python.*manage.py runserver" 2> /dev/null || true

            # Collect static files first
            collect_static

            log_info "Deploying production server (requesting sudo access)..."

            # ONE sudo call for everything: copy configs, permissions, stop, cleanup, start
            sudo sh -c "
                # Copy updated configurations
                cp $PROJECT_ROOT/deployment/uwsgi/scitex_cloud_prod.service /etc/systemd/system/scitex_cloud_prod.service
                cp $PROJECT_ROOT/deployment/nginx/scitex_cloud_prod.conf /etc/nginx/sites-available/scitex_cloud_prod.conf
                systemctl daemon-reload

                # Fix permissions before and after
                chown -R ywatanabe:www-data staticfiles/ media/ logs/ run/ 2>/dev/null || true
                chmod -R 775 staticfiles/ media/ logs/ run/ 2>/dev/null || true

                # Stop service and cleanup
                systemctl stop scitex_cloud_prod 2>/dev/null || true
                rm -f /home/ywatanabe/proj/scitex-cloud/run/scitex_cloud.sock 2>/dev/null || true

                # Test and reload nginx
                nginx -t && systemctl reload nginx

                # Start service
                systemctl start scitex_cloud_prod
            "

            sleep 2

            # Check if it started successfully
            if systemctl is-active --quiet scitex_cloud_prod; then
                log_success "Production server started successfully"
                log_info ""
                log_info "===================================================="
                log_success "Production server: Nginx + uWSGI (systemd)"
                log_info "Service: scitex_cloud_prod"
                log_info "Socket: $PROJECT_ROOT/run/scitex_cloud.sock"
                log_info "Access via: https://scitex.ai"
                log_info "===================================================="
                log_info ""
                log_info "Commands:"
                log_info "  Check status:  sudo systemctl status scitex_cloud_prod"
                log_info "  View logs:     sudo journalctl -u scitex_cloud_prod -f"
                log_info "  Stop server:   ./server.sh stop"
            else
                log_error "Failed to start production server"
                log_info "Check logs: sudo journalctl -u scitex_cloud_prod -n 50"
                exit 1
            fi
        else
            # Development mode
            collect_static
            stop_server
            start_dev
        fi
        ;;

    stop)
        stop_server
        ;;

    restart)
        stop_server
        sleep 2
        $0 start -m "$MODE" -p "$PORT"
        ;;

    status)
        show_status
        ;;

    logs)
        view_logs
        ;;

    clean)
        clean_temp
        ;;

    test)
        activate_venv
        cd "$PROJECT_ROOT"
        log_info "Running tests..."
        python manage.py test
        ;;

    shell)
        activate_venv
        cd "$PROJECT_ROOT"
        log_info "Opening Django shell..."
        python manage.py shell
        ;;

    migrate)
        activate_venv
        run_migrations
        ;;

    static)
        activate_venv
        collect_static
        ;;

    *)
        log_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

tail -f ./logs/*

# EOF
