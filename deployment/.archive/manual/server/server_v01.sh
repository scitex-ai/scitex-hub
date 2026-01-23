#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-25 08:35:23 (ywatanabe)"
# File: ./deployment/server/server.sh

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

echo_header() { echo_info "==== $1 ==="; }

# SciTeX-Cloud Start Script
# Based on best practices from airight project

APP_HOME="/home/ywatanabe/proj/scitex-cloud"
PYTHON_ENV="$APP_HOME/.venv"
PYTHON_BIN="$APP_HOME/.venv/bin/python"
MANAGE_PY="$PYTHON_BIN manage.py"
LOG_DIR="$APP_HOME/logs"
PID_FILE="$APP_HOME/run/scitex.pid"

# Create necessary directories
mkdir -p "$LOG_DIR" "$APP_HOME/run"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -m, --migrate          Run database migrations (makemigrations + migrate)"
    echo "  -c, --collectstatic    Collect static files"
    echo "  -s, --stop             Stop the server and exit"
    echo "  -p, --production       Start in production mode"
    echo "  -d, --daemon           Run in background (daemon mode)"
    echo "  --skip-migrate         Skip database migrations (not recommended)"
    echo "  --skip-static          Skip collecting static files (not recommended)"
    echo "  -h, --help             Show this help message"
    echo
    echo "Description:"
    echo "  This script automatically handles:"
    echo "  1. Killing existing processes on port 8000"
    echo "  2. Running database migrations"
    echo "  3. Collecting static files"
    echo "  4. Starting the server"
    echo "  5. Tailing logs"
    echo
    echo "Examples:"
    echo "  $0                     # Standard start (migrate + static + dev server + logs)"
    echo "  $0 -d                  # Start dev server in background"
    echo "  $0 -p                  # Start production server"
    echo "  $0 -m                  # Only run migrations"
    echo "  $0 -c                  # Only collect static files"
    echo "  $0 -s                  # Stop the server"
    echo "  $0 -cms                # Collect static, run migrations, then stop"
    echo "  $0 --skip-migrate      # Skip migrations (faster for quick testing)"
    exit 1
}

# Ensure proper file permissions
ensure_permissions() {
    echo_header "Ensure permissions..."
    chmod 755 "$APP_HOME/scripts"/*.sh 2> /dev/null || true
    chmod 755 "$APP_HOME/manage.py" 2> /dev/null || true
    echo "Done"
}

# Run database migrations
migrate() {
    echo_header "Running database migrations..."
    $MANAGE_PY makemigrations
    $MANAGE_PY migrate
    echo "Done"
}

# Collect static files
collect_static() {
    echo_header "Collecting static files..."
    $MANAGE_PY collectstatic --noinput
    echo "Done"
}

# Stop any existing servers
stop_existing() {
    echo_header "Stopping existing processes..."

    {
        # Sudo check; if not sudo, exit
        sudo echo "Sudo needed" || exit

        # Kill all Django runserver processes (with and without sudo)
        pkill -9 -f "runserver" 2> /dev/null || true
        sudo pkill -9 -f "runserver" 2> /dev/null || true

        # Kill all Python processes running manage.py
        pkill -9 -f "python.*manage.py" 2> /dev/null || true
        sudo pkill -9 -f "python.*manage.py" 2> /dev/null || true

        # Kill processes using port 8000
        sudo fuser -k -9 8000/tcp 2> /dev/null || true
        fuser -k -9 8000/tcp 2> /dev/null || true

        # Kill any processes listening on port 8000 using lsof
        if command -v lsof &> /dev/null; then
            lsof -ti:8000 2> /dev/null | xargs -r kill -9 2> /dev/null || true
            sudo lsof -ti:8000 2> /dev/null | xargs -r sudo kill -9 2> /dev/null || true
        fi

        # Kill existing uwsgi processes
        pkill -9 -f "uwsgi.*scitex" 2> /dev/null || true
        sudo pkill -9 -f "uwsgi.*scitex" 2> /dev/null || true

        # Remove PID file
        rm -f "$PID_FILE" 2> /dev/null || true

        # Remove uwsgi socket
        rm -f "$APP_HOME/run/uwsgi.sock" 2> /dev/null || true

        # Wait a moment for processes to fully terminate
        sleep 1
    } 2>&1 | grep -v "Killed" || true

    echo_success "Done"
}

# Start development server
start_dev() {
    echo_header "Starting SciTeX-Cloud development server..."

    if [[ "$1" == "daemon" ]]; then
        nohup $MANAGE_PY runserver 127.0.0.1:8000 > "$LOG_DIR/django.log" 2>&1 &
        DJANGO_PID=$!
        echo $DJANGO_PID > "$PID_FILE"
        echo_info "    Development server started in background (PID: $DJANGO_PID)"
        echo_info "    Logs: tail -f $LOG_DIR/django.log"
        echo_info "    Stop with: kill $DJANGO_PID"
    else
        echo_info "    Starting at http://localhost:8000"
        echo_info "    Press Ctrl+C to stop"
        $MANAGE_PY runserver 0.0.0.0:8000 &
        DJANGO_PID=$!
        echo $DJANGO_PID > "$PID_FILE"
        echo_info "    Django PID: $DJANGO_PID"
    fi

    echo "Done"
}

# Start production server with uwsgi
start_prod() {
    echo_header "Starting SciTeX-Cloud production server..."

    # Ensure nginx is configured
    if ! nginx -t 2> /dev/null; then
        echo_warn "    Nginx configuration not found or invalid"
        echo_warn "    Please configure nginx before running in production"
    fi

    # Start uwsgi
    "$APP_HOME/env/bin/uwsgi" --ini "$APP_HOME/config/uwsgi.ini" \
        --daemonize "$LOG_DIR/uwsgi.log" \
        --pidfile "$PID_FILE"

    echo_info "    Production server started with uwsgi"
    echo_info "    Logs: tail -f $LOG_DIR/uwsgi.log"
}

# Main function
main() {
    local do_migrate=false
    local do_collect_static=false
    local do_stop=false
    local is_prod=false
    local start_server=true # Default: start server

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -[mcspd]*)
                # Handle combined flags like -cms, -mc, etc.
                local flags="${1#-}"
                for ((i = 0; i < ${#flags}; i++)); do
                    case "${flags:$i:1}" in
                        m) do_migrate=true ;;
                        c) do_collect_static=true ;;
                        s) do_stop=true ;;
                        p) is_prod=true ;;
                        *)
                            echo "Unknown flag: -${flags:$i:1}"
                            usage
                            ;;
                    esac
                done
                ;;
            --migrate) do_migrate=true ;;
            --collectstatic | --collect-static) do_collect_static=true ;;
            --stop) do_stop=true ;;
            --production) is_prod=true ;;
            --skip-migrate) do_migrate=false ;;
            --skip-static) do_collect_static=false ;;
            -h | --help) usage ;;
            *)
                echo "Unknown option: $1"
                usage
                ;;
        esac
        shift
    done

    # Activate virtual environment
    source "$PYTHON_ENV/bin/activate"

    # If stop flag is set, stop and exit
    if $do_stop; then
        stop_existing
    fi

    # Cleanup Logs
    rm $LOG_DIR/*.log -f

    # In production, always migrate and collect static (no skip allowed)
    if $is_prod; then
        do_migrate=true
        do_collect_static=true
    fi

    # Ensure permissions
    ensure_permissions

    # Run migrations if requested
    if $do_migrate; then
        migrate
    fi

    # Collect static files if requested
    if $do_collect_static; then
        collect_static
    fi

    # Start server if requested
    if $start_server && $is_prod; then
        start_prod
    fi

    if $start_server && $is_dev; then
        start_dev
    fi
}

# Cleanup function for Ctrl+C
cleanup() {
    echo
    echo_warning "Shutting down SciTeX-Cloud..."

    # Kill Django server if PID file exists
    if [ -f "$PID_FILE" ]; then
        DJANGO_PID=$(cat "$PID_FILE")
        if kill -0 $DJANGO_PID 2> /dev/null; then
            echo_info "Stopping Django server (PID: $DJANGO_PID)..."
            kill -TERM $DJANGO_PID 2> /dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 $DJANGO_PID 2> /dev/null; then
                kill -9 $DJANGO_PID 2> /dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Kill any remaining processes on port 8000
    fuser -k 8000/tcp 2> /dev/null || true

    echo_success "✓ SciTeX-Cloud stopped"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Run main function with all arguments
main "$@"

# If not daemon mode, tail logs and wait for Django server
if [ -f "$PID_FILE" ]; then
    DJANGO_PID=$(cat "$PID_FILE")
    echo_info "Tailing logs (Ctrl+C to stop)..."
    tail -f $LOG_DIR/*.log &
    TAIL_PID=$!

    # Wait for Django server process
    wait $DJANGO_PID 2> /dev/null || true

    # Kill tail when Django stops
    kill $TAIL_PID 2> /dev/null || true
fi

# EOF
