#!/bin/bash
# Simple template watcher for minimal Django reload
# Watches **/templates/**/*.html and sends reload signal to Daphne

WATCH_DIRS="/app/apps/*/templates /app/templates"
LOG_FILE="/app/logs/template-watch.log"

echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] Template watcher started" > "$LOG_FILE"
echo -e "   Watching: $WATCH_DIRS" >> "$LOG_FILE"

# Find Daphne PID and send SIGHUP when templates change
while true; do
    # Use inotifywait to watch for template changes
    inotifywait -r -e modify,create,delete,move \
        --exclude '\.(pyc|swp|tmp)$' \
        --format '%w%f' \
        $WATCH_DIRS 2>> "$LOG_FILE" | \
    while read file; do
        if [[ "$file" =~ \.html$ ]]; then
            echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] Template changed: $file" >> "$LOG_FILE"

            # Find Daphne process and send reload signal
            DAPHNE_PID=$(pgrep -f "daphne.*config.asgi:application" | head -1)
            if [ -n "$DAPHNE_PID" ]; then
                echo -e "   Sending reload signal to Daphne (PID: $DAPHNE_PID)" >> "$LOG_FILE"
                kill -HUP "$DAPHNE_PID" 2>> "$LOG_FILE" || true
            else
                echo -e "   Warning: Daphne process not found" >> "$LOG_FILE"
            fi
        fi
    done

    # If inotifywait exits, wait a bit before restarting
    sleep 1
done
