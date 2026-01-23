#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-05-22 04:50:00 (ywatanabe)"
# File: ./scripts/monitor.sh

# SciTeX Cloud Server Monitoring Script

APP_HOME="/home/ywatanabe/proj/SciTeX-Cloud"
LOG_DIR="/var/log/scitex-cloud"

# ANSI colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[OK]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_header() {
    echo "======================================"
    echo "    SciTeX Cloud Server Monitor"
    echo "======================================"
    echo "Timestamp: $(date)"
    echo ""
}

check_processes() {
    echo_info "Checking running processes..."

    # Check Django development server
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo_success "Django development server is running"
        DEV_PID=$(pgrep -f "manage.py runserver")
        echo "  PID: $DEV_PID"
    else
        echo_warning "Django development server is not running"
    fi

    # Check uWSGI
    if pgrep -f uwsgi > /dev/null; then
        echo_success "uWSGI is running"
        UWSGI_PIDS=$(pgrep -f uwsgi | tr '\n' ' ')
        echo "  PIDs: $UWSGI_PIDS"
    else
        echo_warning "uWSGI is not running"
    fi

    # Check Nginx
    if pgrep -f nginx > /dev/null; then
        echo_success "Nginx is running"
    else
        echo_warning "Nginx is not running"
    fi

    echo ""
}

check_ports() {
    echo_info "Checking open ports..."

    # Check port 8000 (Django/uWSGI)
    if netstat -tuln 2> /dev/null | grep -q ":8000 "; then
        echo_success "Port 8000 is open"
        PROC_8000=$(lsof -ti:8000 2> /dev/null || echo "unknown")
        echo "  Process: $PROC_8000"
    else
        echo_warning "Port 8000 is not open"
    fi

    # Check port 80 (HTTP)
    if netstat -tuln 2> /dev/null | grep -q ":80 "; then
        echo_success "Port 80 (HTTP) is open"
    else
        echo_warning "Port 80 (HTTP) is not open"
    fi

    # Check port 443 (HTTPS)
    if netstat -tuln 2> /dev/null | grep -q ":443 "; then
        echo_success "Port 443 (HTTPS) is open"
    else
        echo_warning "Port 443 (HTTPS) is not open"
    fi

    echo ""
}

check_application() {
    echo_info "Checking application health..."

    # Test local connection
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
        echo_success "Application responds on localhost:8000"
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2> /dev/null || echo "000")
        echo_error "Application not responding on localhost:8000 (HTTP $HTTP_CODE)"
    fi

    # Test WSL IP connection
    WSL_IP=$(ip -4 addr show eth0 2> /dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "127.0.0.1")
    if curl -s -o /dev/null -w "%{http_code}" http://$WSL_IP:8000/ | grep -q "200"; then
        echo_success "Application responds on $WSL_IP:8000"
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$WSL_IP:8000/ 2> /dev/null || echo "000")
        echo_warning "Application not responding on $WSL_IP:8000 (HTTP $HTTP_CODE)"
    fi

    echo ""
}

check_logs() {
    echo_info "Checking recent log entries..."

    # Django logs
    if [ -f "$APP_HOME/logs/django.log" ]; then
        echo_info "Recent Django log entries:"
        tail -n 5 "$APP_HOME/logs/django.log" | sed 's/^/  /'
    else
        echo_warning "Django log file not found"
    fi

    # uWSGI logs
    if [ -f "$LOG_DIR/uwsgi.log" ]; then
        echo_info "Recent uWSGI log entries:"
        tail -n 3 "$LOG_DIR/uwsgi.log" | sed 's/^/  /'
    else
        echo_warning "uWSGI log file not found"
    fi

    echo ""
}

check_disk_space() {
    echo_info "Checking disk space..."

    # Check main application directory
    DISK_USAGE=$(df -h "$APP_HOME" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 80 ]; then
        echo_success "Disk usage: ${DISK_USAGE}% (OK)"
    elif [ "$DISK_USAGE" -lt 90 ]; then
        echo_warning "Disk usage: ${DISK_USAGE}% (Warning)"
    else
        echo_error "Disk usage: ${DISK_USAGE}% (Critical)"
    fi

    # Check log directory if it exists
    if [ -d "$LOG_DIR" ]; then
        LOG_SIZE=$(du -sh "$LOG_DIR" 2> /dev/null | cut -f1 || echo "unknown")
        echo_info "Log directory size: $LOG_SIZE"
    fi

    echo ""
}

check_memory() {
    echo_info "Checking memory usage..."

    # Overall memory usage
    MEMORY_INFO=$(free -h | grep "Mem:")
    echo_info "Memory: $MEMORY_INFO"

    # Check for memory-intensive processes
    if pgrep -f "python.*manage.py" > /dev/null; then
        PYTHON_MEM=$(ps -o pid,pmem,comm -C python3 | grep -v PID | head -5)
        if [ ! -z "$PYTHON_MEM" ]; then
            echo_info "Python processes memory usage:"
            echo "$PYTHON_MEM" | sed 's/^/  /'
        fi
    fi

    echo ""
}

show_summary() {
    echo "======================================"
    echo "           SUMMARY"
    echo "======================================"

    # Count issues
    ERROR_COUNT=$(grep -c "ERROR" /tmp/monitor_output 2> /dev/null || echo "0")
    WARNING_COUNT=$(grep -c "WARNING" /tmp/monitor_output 2> /dev/null || echo "0")

    if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
        echo_success "All systems operational"
    elif [ "$ERROR_COUNT" -eq 0 ]; then
        echo_warning "$WARNING_COUNT warning(s) found"
    else
        echo_error "$ERROR_COUNT error(s) and $WARNING_COUNT warning(s) found"
    fi

    echo ""
    echo_info "For detailed logs, check:"
    echo "  Django logs: $APP_HOME/logs/"
    echo "  System logs: $LOG_DIR/"

    echo ""
    echo_info "To restart services: ./scripts/server.sh windows"
    echo_info "To check server status: ./scripts/monitor.sh"
}

# Main execution
{
    show_header
    check_processes
    check_ports
    check_application
    check_logs
    check_disk_space
    check_memory
    show_summary
} | tee /tmp/monitor_output

# EOF
