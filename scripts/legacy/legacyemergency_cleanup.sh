#!/bin/bash
# Emergency cleanup script for port 8000

echo "===== EMERGENCY CLEANUP ====="
echo ""

echo "[1/4] Killing all Python Django runserver processes..."
sudo pkill -9 -f "python.*manage.py runserver" 2> /dev/null \
    || pkill -9 -f "python.*manage.py runserver" 2> /dev/null || true
sleep 1

echo "[2/4] Killing all processes on port 8000 with fuser..."
sudo fuser -k 8000/tcp 2> /dev/null \
    || fuser -k 8000/tcp 2> /dev/null || true
sleep 1

echo "[3/4] Killing all processes on port 8000 with lsof..."
PIDS=$(sudo lsof -ti:8000 2> /dev/null || lsof -ti:8000 2> /dev/null || true)
if [ -n "$PIDS" ]; then
    echo "Found PIDs: $PIDS"
    echo "$PIDS" | xargs -r sudo kill -9 2> /dev/null \
        || echo "$PIDS" | xargs -r kill -9 2> /dev/null || true
fi
sleep 1

echo "[4/4] Final verification..."
if sudo lsof -ti:8000 2> /dev/null || lsof -ti:8000 2> /dev/null; then
    echo "❌ WARNING: Port 8000 may still be in use!"
    echo ""
    echo "Processes on port 8000:"
    sudo lsof -i:8000 2> /dev/null || lsof -i:8000 2> /dev/null \
        || sudo ss -tulpn | grep :8000 || ss -tulpn | grep :8000 \
        || sudo netstat -tulpn | grep :8000 || netstat -tulpn | grep :8000
    echo ""
    echo "You may need to manually kill these processes or reboot."
else
    echo "✅ SUCCESS: Port 8000 is now free!"
fi

echo ""
echo "Cleanup complete. You can now run: ./server.sh -m windows"
