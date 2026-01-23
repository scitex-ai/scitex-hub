#!/bin/bash
# SciTeX Cloud Server Launcher - Simple & Essential

APP_HOME="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${CYAN}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }

# Show help
show_help() {
    echo_info "SciTeX Cloud Server Launcher"
    echo "Usage: ./server.sh [mode]"
    echo ""
    echo "Modes:"
    echo "  dev     - Development server (default)"
    echo "  win     - Development with Windows access"
    echo "  prod    - Production server"
    echo ""
    exit 0
}

# Set mode
MODE="${1:-dev}"
case $MODE in
    dev|win|prod) ;;
    --help|-h) show_help ;;
    *) echo_error "Invalid mode: $MODE"; show_help ;;
esac

# Stop any running servers first
echo_info "🛑 Stopping any running servers..."
"$APP_HOME/stop.sh"

# Load secrets
SECRETS_FILE="/home/ywatanabe/.bash.d/secrets/000_ENV_SCITEX.src"
[ -f "$SECRETS_FILE" ] && source "$SECRETS_FILE"

# Activate virtual environment
if [ -d "$APP_HOME/.env" ]; then
    source "$APP_HOME/.env/bin/activate"
else
    echo_error "Virtual environment not found. Run: python3 -m venv .env"
    exit 1
fi

# Set Django settings
case $MODE in
    dev|win) export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.development ;;
    prod) export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.production ;;
esac

# Basic setup
echo_info "🔍 Running system checks..."
python manage.py check

echo_info "🗄️ Applying migrations..."
python manage.py migrate --verbosity=1

echo_info "📁 Collecting static files..."
python manage.py collectstatic --noinput --verbosity=0

# Start server
case $MODE in
    dev)
        echo_success "✅ Starting development server..."
        echo_info "🌐 Available at: http://localhost:8000"
        python manage.py runserver
        ;;
    win)
        WSL_IP=$(ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "127.0.0.1")
        echo_success "✅ Starting development server with Windows access..."
        echo_info "🌐 Windows URL: http://$WSL_IP:8000"
        python manage.py runserver 0.0.0.0:8000
        ;;
    prod)
        echo_success "✅ Starting production server..."
        echo_info "🌐 Available at: https://scitex.ai"
        if command -v uwsgi &> /dev/null; then
            # Start uWSGI in background
            uwsgi --ini /home/ywatanabe/proj/SciTeX-Cloud/config/uwsgi_simple.ini &
            UWSGI_PID=$!
            
            # Wait a moment for server to start
            sleep 2
            
            # Setup log files
            LOG_DIR="/home/ywatanabe/proj/SciTeX-Cloud/logs"
            mkdir -p "$LOG_DIR"
            
            # Function to cleanup on exit
            cleanup() {
                echo_info "🛑 Stopping production server..."
                kill $UWSGI_PID 2>/dev/null
                exit 0
            }
            trap cleanup SIGINT SIGTERM
            
            echo_success "🚀 Production server started successfully!"
            echo_info "📊 Monitoring essential logs only (Ctrl+C to stop)..."
            echo_info "📄 Full logs available in: $LOG_DIR"
            
            # Monitor only error logs and recent entries
            if [ -f "$LOG_DIR/error.log" ]; then
                tail -f "$LOG_DIR/error.log" 2>/dev/null | grep -E "(ERROR|CRITICAL|Exception)" --line-buffered
            else
                echo_info "⏳ Waiting for error logs..."
                while [ ! -f "$LOG_DIR/error.log" ]; do
                    sleep 1
                done
                tail -f "$LOG_DIR/error.log" 2>/dev/null | grep -E "(ERROR|CRITICAL|Exception)" --line-buffered
            fi
        else
            echo_error "❌ uWSGI not found!"
            exit 1
        fi
        ;;
