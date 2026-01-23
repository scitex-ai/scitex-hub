#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-25 16:21:48 (ywatanabe)"
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
    sudo chmod 755 "$APP_HOME/scripts"/*.sh 2> /dev/null || true
    sudo chmod 755 "$APP_HOME/manage.py" 2> /dev/null || true
    sudo chmod 775 $HOME/.logs 2> /dev/null || true

    # Note: For production deployment with www-data user, run these commands once:
    sudo chmod o+x /home/ywatanabe 2> /dev/null || true
    sudo rm -f /home/ywatanabe/.scitex/logs/*
    sudo chown -R www-data:www-data /home/ywatanabe/.scitex 2> /dev/null || true
    sudo chmod -R 777 /home/ywatanabe/.scitex 2> /dev/null || true

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

    local STOPPED_SOMETHING=false

    # Kill auto-collectstatic process if exists
    local COLLECT_PID_FILE="$APP_HOME/run/collectstatic.pid"
    if [ -f "$COLLECT_PID_FILE" ]; then
        COLLECT_PID=$(cat "$COLLECT_PID_FILE")
        if kill -0 $COLLECT_PID 2> /dev/null; then
            echo_info "    Stopping auto-collectstatic (PID: $COLLECT_PID)..."
            kill -TERM $COLLECT_PID 2> /dev/null || true
            STOPPED_SOMETHING=true
        fi
        rm -f "$COLLECT_PID_FILE"
    fi

    # Stop uwsgi using PID file
    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")
        if kill -0 $SERVER_PID 2> /dev/null; then
            if ps -p $SERVER_PID -o comm= | grep -q uwsgi; then
                echo_info "    Stopping uwsgi (PID: $SERVER_PID)..."
                kill -INT $SERVER_PID 2> /dev/null || kill -TERM $SERVER_PID 2> /dev/null || true

                # Wait for graceful shutdown
                for i in {1..5}; do
                    if ! kill -0 $SERVER_PID 2> /dev/null; then
                        break
                    fi
                    sleep 1
                done

                # Force if needed
                if kill -0 $SERVER_PID 2> /dev/null; then
                    kill -9 $SERVER_PID 2> /dev/null || true
                fi
                STOPPED_SOMETHING=true
            else
                echo_info "    Stopping Django server (PID: $SERVER_PID)..."
                kill -TERM $SERVER_PID 2> /dev/null || kill -9 $SERVER_PID 2> /dev/null || true
                STOPPED_SOMETHING=true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Fallback: kill any Django/uwsgi processes
    if pkill -0 -f "uwsgi.*scitex" 2> /dev/null; then
        echo_info "    Cleaning up stray uwsgi processes..."
        pkill -TERM -f "uwsgi.*scitex" 2> /dev/null || true
        sleep 2
        pkill -9 -f "uwsgi.*scitex" 2> /dev/null || true
        STOPPED_SOMETHING=true
    fi

    if pkill -0 -f "runserver" 2> /dev/null; then
        echo_info "    Cleaning up Django runserver..."
        pkill -TERM -f "runserver" 2> /dev/null || true
        sleep 1
        pkill -9 -f "runserver" 2> /dev/null || true
        STOPPED_SOMETHING=true
    fi

    # Clean up sockets
    rm -f "$APP_HOME/run/scitex_cloud.sock" "$APP_HOME/run/uwsgi.sock" 2> /dev/null || true

    # Kill processes on port 8000 (dev mode)
    if fuser 8000/tcp 2> /dev/null; then
        echo_info "    Freeing port 8000..."
        fuser -k -TERM 8000/tcp 2> /dev/null || true
        sleep 1
        fuser -k -9 8000/tcp 2> /dev/null || true
        STOPPED_SOMETHING=true
    fi

    if $STOPPED_SOMETHING; then
        echo_success "    Existing processes stopped"
    else
        echo_info "    No running processes found"
    fi

    sleep 1
}

# Continuous static collection for development (runs every 10 seconds)
peiodic_collect_static() {
    local COLLECT_PID_FILE="$APP_HOME/run/collectstatic.pid"

    # Background loop for collecting static files
    (
        while true; do
            echo_header "Starting auto-collectstatic (every 10s)..."
            $MANAGE_PY collectstatic --noinput --clear > /dev/null 2>&1
            sleep 10
        done
    ) &

    local AUTO_COLLECT_PID=$!
    echo $AUTO_COLLECT_PID > "$COLLECT_PID_FILE"
    echo_info "    Auto-collectstatic started (PID: $AUTO_COLLECT_PID)"
    echo "Done"
}

# Start development server
start_dev() {
    echo_header "Starting SciTeX-Cloud development server..."

    # Start auto-collectstatic in dev mode
    peiodic_collect_static

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

    # Setup required directories
    echo_info "    Setting up directories..."
    mkdir -p /home/ywatanabe/.scitex/logs
    mkdir -p "$APP_HOME/run"
    mkdir -p "$APP_HOME/logs"

    # Then uncomment uid/gid in uwsgi_prod.ini

    # Ensure nginx is configured
    if ! nginx -t 2> /dev/null; then
        echo_warning "    Nginx configuration not found or invalid"
        echo_warning "    Please configure nginx before running in production"
    fi

    # Start uwsgi
    "$PYTHON_ENV/bin/uwsgi" \
        --ini "$APP_HOME/deployment/uwsgi/uwsgi_prod.ini" \
        --daemonize "$LOG_DIR/uwsgi.log" \
        --pidfile "$PID_FILE"

    # Wait for uwsgi to start and verify
    sleep 3
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2> /dev/null; then
        echo_success "    Production server started with uwsgi (PID: $(cat $PID_FILE))"
        echo_info "    Socket: $APP_HOME/run/scitex_cloud.sock"
        echo_info "    Logs: tail -f $LOG_DIR/uwsgi.log"
        echo_info "    Stop with: ./server -s"
    else
        echo_error "    Failed to start uwsgi - check logs:"
        tail -50 /var/log/uwsgi/scitex_cloud.log 2> /dev/null || tail -50 "$LOG_DIR/uwsgi.log"
        return 1
    fi
}

# Main function
main() {
    rm ./logs/*.log -f

    local do_migrate=false
    local do_collect_static=false
    local do_stop=false
    local is_prod=false
    local is_dev=true       # Default: dev mode
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
                        p)
                            is_prod=true
                            is_dev=false
                            ;;
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
            --production)
                is_prod=true
                is_dev=false
                ;;
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
        exit 0
    fi

    # # Rotate logs instead of deleting (keep last 5 files)
    # for logfile in $LOG_DIR/*.log; do
    #     if [ -f "$logfile" ] && [ $(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile" 2>/dev/null) -gt 10485760 ]; then
    #         # Archive logs > 10MB
    #         mv "$logfile" "$logfile.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    #         # Keep only last 5 archived logs
    #         ls -t "$logfile".* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    #     fi
    # done

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

# Cleanup function for Ctrl+C and graceful shutdown
cleanup() {
    echo
    echo_header "Shutting down SciTeX-Cloud..."

    # Kill auto-collectstatic process if exists
    local COLLECT_PID_FILE="$APP_HOME/run/collectstatic.pid"
    if [ -f "$COLLECT_PID_FILE" ]; then
        COLLECT_PID=$(cat "$COLLECT_PID_FILE")
        if kill -0 $COLLECT_PID 2> /dev/null; then
            echo_info "    Stopping auto-collectstatic (PID: $COLLECT_PID)..."
            kill -TERM $COLLECT_PID 2> /dev/null || true
            sleep 1
            # Force kill if still running
            if kill -0 $COLLECT_PID 2> /dev/null; then
                kill -9 $COLLECT_PID 2> /dev/null || true
            fi
        fi
        rm -f "$COLLECT_PID_FILE"
    fi

    # Handle server shutdown (both dev and prod)
    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")
        if kill -0 $SERVER_PID 2> /dev/null; then
            # Check if it's uwsgi or Django runserver
            if ps -p $SERVER_PID -o comm= | grep -q uwsgi; then
                echo_info "    Stopping uwsgi server (PID: $SERVER_PID)..."
                # Graceful shutdown for uwsgi
                kill -INT $SERVER_PID 2> /dev/null || true

                # Wait up to 10 seconds for graceful shutdown
                for i in {1..10}; do
                    if ! kill -0 $SERVER_PID 2> /dev/null; then
                        break
                    fi
                    sleep 1
                done

                # Force kill if still running
                if kill -0 $SERVER_PID 2> /dev/null; then
                    echo_warning "    Graceful shutdown timeout, forcing..."
                    kill -9 $SERVER_PID 2> /dev/null || true
                fi

                # Clean up socket
                rm -f "$APP_HOME/run/scitex_cloud.sock" 2> /dev/null || true
            else
                echo_info "    Stopping Django server (PID: $SERVER_PID)..."
                kill -TERM $SERVER_PID 2> /dev/null || true
                sleep 2
                # Force kill if still running
                if kill -0 $SERVER_PID 2> /dev/null; then
                    kill -9 $SERVER_PID 2> /dev/null || true
                fi
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Kill any remaining processes on port 8000 (dev mode)
    fuser -k 8000/tcp 2> /dev/null || true

    echo_success "    ✓ SciTeX-Cloud stopped"
    exit 0
}

tail_log() {
    echo
    sleep 3
    echo_header "Tailing logs (Ctrl+C to stop)..."

    # Determine which log to tail based on what's running
    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")

        # Check if it's uwsgi or Django runserver
        if ps -p $SERVER_PID -o comm= 2> /dev/null | grep -q uwsgi; then
            # For production uwsgi, tail both uwsgi and Django logs
            echo_info "    Following production logs..."
            tail -f "$LOG_DIR/uwsgi.log" /var/log/uwsgi/scitex_cloud.log "$LOG_DIR/error.log" 2> /dev/null &
            TAIL_PID=$!

            # Keep tailing until interrupted
            wait $TAIL_PID 2> /dev/null || true
        else
            # For dev server, tail all logs
            tail -f $LOG_DIR/*.log &
            TAIL_PID=$!

            # Wait for Django server process
            wait $SERVER_PID 2> /dev/null || true

            # Kill tail when Django stops
            kill $TAIL_PID 2> /dev/null || true
        fi
    fi
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Run main function with all arguments
main "$@"

# # tail_log
# tail_log

# EOF
