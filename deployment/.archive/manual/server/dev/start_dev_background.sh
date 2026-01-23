#!/bin/bash
# Start Django development server in background with proper environment

# Set the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Kill any existing Django servers on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Set environment variables
export SCITEX_CLOUD_DJANGO_SECRET_KEY='django-insecure-development-key-12345'
export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.development

# Start the server in background
echo "Starting Django development server..."
nohup python manage.py runserver 0.0.0.0:8000 > server.log 2>&1 &
SERVER_PID=$!

echo "Server started with PID: $SERVER_PID"
echo "Logs available at: $PROJECT_ROOT/server.log"

# Wait a moment for server to start
sleep 3

# Check if server is running
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200\|302"; then
    echo "✅ Server is running at http://localhost:8000/"
    echo "✅ Also accessible at http://172.19.33.56:8000/"
else
    echo "⚠️  Server may have issues. Check server.log for details."
