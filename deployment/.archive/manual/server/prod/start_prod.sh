#!/bin/bash
# SciTeX Cloud Production Server Startup Script

set -e  # Exit on any error

echo "🏭 Starting SciTeX Cloud Production Server..."

# Load environment variables from centralized secrets
SECRETS_FILE="/home/ywatanabe/.bash.d/secrets/000_ENV_SCITEX.src"
if [ -f "$SECRETS_FILE" ]; then
    echo "🔐 Loading environment variables from centralized secrets..."
    source "$SECRETS_FILE"
else
    echo "⚠️ Centralized secrets file not found: $SECRETS_FILE"
    echo "💡 Using fallback environment settings"
fi

# Activate virtual environment
if [ -d "env" ]; then
    source env/bin/activate
else
    echo "❌ Virtual environment not found! Run start_dev.sh first."
    exit 1
fi

# Set up log directories
LOG_DIR="/var/log/scitex-cloud"
if [ ! -d "$LOG_DIR" ]; then
    echo "📂 Creating log directory at $LOG_DIR..."
    # Use sudo if running as non-root user
    if [ $(id -u) -ne 0 ]; then
        sudo mkdir -p $LOG_DIR
        sudo chmod 755 $LOG_DIR
        sudo chown -R $(whoami):$(whoami) $LOG_DIR
    else
        mkdir -p $LOG_DIR
        chmod 755 $LOG_DIR
    fi
fi

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Set production environment
export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.production

# Run Django checks
echo "🔍 Running Django system checks (production)..."
python manage.py check --deploy

# Apply database migrations
echo "🗄️  Applying database migrations..."
python manage.py migrate

# Collect static files for production
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Check for uWSGI installation
if command -v uwsgi &> /dev/null; then
    UWSGI_INSTALLED=true
else
    UWSGI_INSTALLED=false
    echo "❌ uWSGI not found! Installing uWSGI..."
    pip install uwsgi
    UWSGI_INSTALLED=true
fi

echo ""
echo "✅ Production setup complete!"
echo ""

# Start the server
if [ "$1" = "--start" ]; then
    if [ "$UWSGI_INSTALLED" = true ]; then
        echo "🚀 Starting uWSGI server..."
        uwsgi --ini config/uwsgi.ini
    else
        echo "❌ uWSGI not installed!"
        exit 1
    fi
else
    echo "🌍 To start with uWSGI:"
    echo "   uwsgi --ini config/uwsgi.ini"
    echo ""
    echo "📊 Logs are available at: $LOG_DIR"
    echo "   - Application logs: $LOG_DIR/app.log"
    echo "   - Django logs: $LOG_DIR/django.log"
    echo "   - Error logs: $LOG_DIR/error.log"
    echo "   - uWSGI logs: $LOG_DIR/uwsgi.log"
    echo ""
    echo "🚀 Run with --start flag to automatically start the server"
    echo "   ./scripts/start_prod.sh --start"
