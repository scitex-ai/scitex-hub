#!/bin/bash
# Kill all processes using port 8000

echo "Killing processes on port 8000..."

# Method 1: fuser
if command -v fuser &> /dev/null; then
    echo "Using fuser..."
    sudo fuser -k 8000/tcp 2> /dev/null || true
fi

# Method 2: lsof
if command -v lsof &> /dev/null; then
    echo "Using lsof..."
    sudo lsof -ti:8000 2> /dev/null | xargs -r sudo kill -9 2> /dev/null || true
fi

# Method 3: pkill
echo "Using pkill..."
sudo pkill -9 -f "python.*manage.py runserver" 2> /dev/null || true
sudo pkill -9 -f "runserver.*8000" 2> /dev/null || true

# Method 4: ss with sudo
echo "Using ss..."
PIDS=$(sudo ss -tulpn 2> /dev/null | grep ':8000' | grep -oP 'pid=\K[0-9]+' || true)
if [ -n "$PIDS" ]; then
    echo "Found PIDs: $PIDS"
    echo "$PIDS" | xargs -r sudo kill -9 2> /dev/null || true
fi

sleep 1
echo "Cleanup complete"

# Check if port is still in use
if sudo lsof -i:8000 2> /dev/null || sudo ss -tulpn 2> /dev/null | grep ':8000'; then
    echo "WARNING: Port 8000 may still be in use"
else
    echo "SUCCESS: Port 8000 is free"
fi
