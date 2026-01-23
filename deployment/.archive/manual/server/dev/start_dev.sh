#!/bin/bash
# SciTeX Cloud Development Server Startup Script

set -e # Exit on any error

echo "🚀 Starting SciTeX Cloud Development Server..."

# Check if virtual environment exists, create if not
if [ ! -d "env" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv env
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source env/bin/activate

# Set Django settings module
export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.development

# Install/upgrade dependencies
echo "📚 Installing development dependencies..."
pip install --upgrade pip
pip install -r docs/requirements/development.txt

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    echo "❌ manage.py not found! Make sure you're in the correct directory."
    exit 1
fi

# Run Django checks
echo "🔍 Running Django system checks..."
python manage.py check

# Apply database migrations
echo "🗄️  Applying database migrations..."
python manage.py migrate

# Collect static files (for development testing)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if needed (optional)
echo "👤 Creating superuser (optional, press Ctrl+C to skip)..."
python manage.py createsuperuser --noinput --username admin --email admin@scitex.ai || echo "Superuser creation skipped"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting development server at http://127.0.0.1:8000"
echo "📝 Admin panel available at http://127.0.0.1:8000/admin"
echo "🔄 Hot reload enabled - changes will auto-refresh your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Get the WSL IP address for Windows access
WSL_IP=$(ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
echo ""
echo "🌐 You can access the site from Windows at http://$WSL_IP:8000"
echo "🌐 Or access it via localhost at http://localhost:8000"
echo ""

# Start the development server
