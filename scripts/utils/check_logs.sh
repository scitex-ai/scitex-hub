#!/bin/bash
# Check and display SciTeX Hub log files
# Usage: ./scripts/check_logs.sh [log_type] [lines]
#   log_type: app, django, uwsgi, error, all (default: all)
#   lines: number of lines to show (default: 20)

# Log directory
LOG_DIR="/var/log/scitex-hub"

# Default values
LOG_TYPE=${1:-"all"}
LINES=${2:-20}

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}Error: Log directory $LOG_DIR does not exist!${NC}"
    echo "Are you in development mode? Checking for logs/ directory..."

    if [ -d "./logs" ]; then
        LOG_DIR="./logs"
        echo -e "${GREEN}Found local logs directory. Using it instead.${NC}"
    else
        echo -e "${YELLOW}No logs directory found. Attempting to create logs/ directory...${NC}"
        mkdir -p logs
        LOG_DIR="./logs"
        touch $LOG_DIR/app.log $LOG_DIR/django.log $LOG_DIR/error.log
        echo -e "${GREEN}Created logs directory and log files.${NC}"
    fi
fi

function show_log {
    local file=$1
    local title=$2
    local lines=$3

    if [ -f "$file" ]; then
        echo -e "\n${BLUE}=== $title (last $lines lines) ===${NC}"
        if [ -s "$file" ]; then
            tail -n $lines "$file"
        else
            echo -e "${YELLOW}Log file is empty.${NC}"
        fi
    else
        echo -e "\n${YELLOW}Warning: $title log file does not exist at $file${NC}"
    fi
}

# Display header
echo -e "${GREEN}SciTeX Hub Log Checker${NC}"
echo -e "${CYAN}Log directory: $LOG_DIR${NC}"
echo -e "${CYAN}Showing last $LINES lines${NC}"

# Display logs based on type
case "$LOG_TYPE" in
    "app")
        show_log "$LOG_DIR/app.log" "Application" $LINES
        ;;
    "django")
        show_log "$LOG_DIR/django.log" "Django" $LINES
        ;;
    "uwsgi")
        show_log "$LOG_DIR/uwsgi.log" "uWSGI" $LINES
        ;;
    "gunicorn")
        show_log "$LOG_DIR/gunicorn-access.log" "Gunicorn Access" $LINES
        show_log "$LOG_DIR/gunicorn-error.log" "Gunicorn Error" $LINES
        ;;
    "error")
        show_log "$LOG_DIR/error.log" "Error" $LINES
        ;;
    "nginx")
        if [ -f "/var/log/nginx/scitex-hub-access.log" ]; then
            show_log "/var/log/nginx/scitex-hub-access.log" "Nginx Access" $LINES
            show_log "/var/log/nginx/scitex-hub-error.log" "Nginx Error" $LINES
        else
            echo -e "${YELLOW}Nginx logs not found. They might be in a different location or Nginx isn't installed.${NC}"
        fi
        ;;
    "all")
        show_log "$LOG_DIR/app.log" "Application" $LINES
        show_log "$LOG_DIR/django.log" "Django" $LINES
        show_log "$LOG_DIR/error.log" "Error" $LINES
        show_log "$LOG_DIR/uwsgi.log" "uWSGI" $LINES
        show_log "$LOG_DIR/gunicorn-access.log" "Gunicorn Access" $LINES
        show_log "$LOG_DIR/gunicorn-error.log" "Gunicorn Error" $LINES

        # Check if Nginx is installed and logs exist
        if [ -f "/var/log/nginx/scitex-hub-access.log" ]; then
            show_log "/var/log/nginx/scitex-hub-access.log" "Nginx Access" $LINES
            show_log "/var/log/nginx/scitex-hub-error.log" "Nginx Error" $LINES
        fi
        ;;
    *)
        echo -e "${RED}Error: Unknown log type '$LOG_TYPE'${NC}"
        echo "Available types: app, django, uwsgi, gunicorn, error, nginx, all"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Done checking logs.${NC}"
