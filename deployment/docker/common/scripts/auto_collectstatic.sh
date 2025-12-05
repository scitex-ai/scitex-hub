#!/bin/bash
# Auto-collect static files every 10 seconds (development only)

echo -e "Starting auto-collectstatic (every 10 seconds)..."

while true; do
    python manage.py collectstatic --noinput --clear > /dev/null 2>&1
    sleep 10
done
