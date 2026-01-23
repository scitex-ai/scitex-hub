#!/bin/bash
# SciTeX Cloud Production Monitoring Script

APP_HOME="/home/ywatanabe/proj/SciTeX-Cloud"
PRODUCTION_URL="https://scitex.ai"

# ANSI colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[OK]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_highlight() { echo -e "${CYAN}[METRIC]${NC} $1"; }

show_header() {
    echo "=============================================="
    echo "    SciTeX Cloud Production Monitor"
    echo "=============================================="
    echo "Timestamp: $(date)"
    echo "Production URL: $PRODUCTION_URL"
    echo ""
}

check_production_services() {
    echo_info "Checking production services..."

    # Check Nginx
    if systemctl is-active --quiet nginx; then
        echo_success "Nginx service is active"
    else
        echo_error "Nginx service is not active"
    fi

    # Check uWSGI processes
    if pgrep -f uwsgi > /dev/null; then
        UWSGI_COUNT=$(pgrep -f uwsgi | wc -l)
        echo_success "uWSGI is running ($UWSGI_COUNT workers)"
        UWSGI_PIDS=$(pgrep -f uwsgi | tr '\n' ' ')
        echo_highlight "uWSGI PIDs: $UWSGI_PIDS"
    else
        echo_error "uWSGI is not running"
    fi

    echo ""
}

check_production_endpoints() {
    echo_info "Checking production endpoints..."

    # Main site
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL" 2> /dev/null || echo "000")
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$PRODUCTION_URL" 2> /dev/null || echo "0")

    if [ "$HTTP_CODE" = "200" ]; then
        echo_success "Main site: HTTP $HTTP_CODE (${RESPONSE_TIME}s)"
    else
        echo_error "Main site: HTTP $HTTP_CODE"
    fi

    # API Health Check
    API_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL/api/v1/auth/" 2> /dev/null || echo "000")
    if [ "$API_CODE" = "200" ] || [ "$API_CODE" = "405" ]; then
        echo_success "API endpoints accessible: HTTP $API_CODE"
    else
        echo_warning "API endpoints: HTTP $API_CODE"
    fi

    # Check SSL/Security Headers
    SECURITY_HEADERS=$(curl -s -I "$PRODUCTION_URL" | grep -E "(Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options)" | wc -l)
    if [ "$SECURITY_HEADERS" -ge 3 ]; then
        echo_success "Security headers present ($SECURITY_HEADERS)"
    else
        echo_warning "Missing security headers ($SECURITY_HEADERS/3)"
    fi

    echo ""
}

check_performance_metrics() {
    echo_info "Checking performance metrics..."

    # Response time measurement
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$PRODUCTION_URL" 2> /dev/null)
    RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc -l 2> /dev/null | cut -d. -f1)

    if [ "$RESPONSE_MS" -lt 500 ]; then
        echo_success "Response time: ${RESPONSE_MS}ms (excellent)"
    elif [ "$RESPONSE_MS" -lt 1000 ]; then
        echo_success "Response time: ${RESPONSE_MS}ms (good)"
    elif [ "$RESPONSE_MS" -lt 2000 ]; then
        echo_warning "Response time: ${RESPONSE_MS}ms (acceptable)"
    else
        echo_error "Response time: ${RESPONSE_MS}ms (slow)"
    fi

    # SSL certificate check
    SSL_DAYS=$(openssl s_client -connect scitex.ai:443 -servername scitex.ai < /dev/null 2> /dev/null \
        | openssl x509 -noout -dates 2> /dev/null | grep "notAfter" \
        | cut -d= -f2 | xargs -I {} date -d "{}" +%s 2> /dev/null)

    if [ ! -z "$SSL_DAYS" ]; then
        CURRENT_DATE=$(date +%s)
        DAYS_LEFT=$(((SSL_DAYS - CURRENT_DATE) / 86400))

        if [ "$DAYS_LEFT" -gt 30 ]; then
            echo_success "SSL certificate valid for $DAYS_LEFT days"
        elif [ "$DAYS_LEFT" -gt 7 ]; then
            echo_warning "SSL certificate expires in $DAYS_LEFT days"
        else
            echo_error "SSL certificate expires in $DAYS_LEFT days"
        fi
    else
        echo_warning "Could not check SSL certificate expiration"
    fi

    echo ""
}

check_resource_usage() {
    echo_info "Checking resource usage..."

    # Memory usage
    MEMORY_USED=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    echo_highlight "Memory usage: ${MEMORY_USED}%"

    # Disk usage
    DISK_USAGE=$(df -h "$APP_HOME" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 80 ]; then
        echo_success "Disk usage: ${DISK_USAGE}%"
    elif [ "$DISK_USAGE" -lt 90 ]; then
        echo_warning "Disk usage: ${DISK_USAGE}%"
    else
        echo_error "Disk usage: ${DISK_USAGE}%"
    fi

    # Load average
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)
    echo_highlight "Load average: $LOAD_AVG"

    # uWSGI worker status
    if [ -f "$APP_HOME/uwsgi.log" ]; then
        RECENT_ERRORS=$(tail -n 50 "$APP_HOME/uwsgi.log" 2> /dev/null | grep -i error | wc -l)
        if [ "$RECENT_ERRORS" -eq 0 ]; then
            echo_success "No recent uWSGI errors"
        else
            echo_warning "$RECENT_ERRORS recent uWSGI errors"
        fi
    fi

    echo ""
}

check_application_health() {
    echo_info "Checking application health..."

    # Database connectivity (via Django admin check)
    ADMIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL/admin/" 2> /dev/null || echo "000")
    if [ "$ADMIN_CODE" = "302" ] || [ "$ADMIN_CODE" = "200" ]; then
        echo_success "Database connectivity: OK (HTTP $ADMIN_CODE)"
    else
        echo_warning "Database connectivity: HTTP $ADMIN_CODE"
    fi

    # Static files serving
    STATIC_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL/static/css/main.css" 2> /dev/null || echo "000")
    if [ "$STATIC_CODE" = "200" ]; then
        echo_success "Static files serving: OK"
    else
        echo_warning "Static files serving: HTTP $STATIC_CODE"
    fi

    echo ""
}

show_production_summary() {
    echo "=============================================="
    echo "         PRODUCTION SUMMARY"
    echo "=============================================="

    # Count issues from output
    ERROR_COUNT=$(grep -c "ERROR" /tmp/monitor_prod_output 2> /dev/null || echo "0")
    WARNING_COUNT=$(grep -c "WARNING" /tmp/monitor_prod_output 2> /dev/null || echo "0")

    if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
        echo_success "✅ Production system fully operational"
    elif [ "$ERROR_COUNT" -eq 0 ]; then
        echo_warning "⚠️  $WARNING_COUNT warning(s) - system stable"
    else
        echo_error "🚨 $ERROR_COUNT critical issue(s), $WARNING_COUNT warning(s)"
    fi

    # Quick access info
    echo ""
    echo_info "Quick Access:"
    echo "  🌐 Site: $PRODUCTION_URL"
    echo "  📊 Admin: $PRODUCTION_URL/admin/"
    echo "  🔧 Restart: sudo systemctl restart nginx && ./server.sh prod"
    echo "  📈 Monitor: ./scripts/monitor_prod.sh"

    echo ""
}

# Main execution with output capture
{
    show_header
    check_production_services
    check_production_endpoints
    check_performance_metrics
    check_resource_usage
    check_application_health
    show_production_summary
} | tee /tmp/monitor_prod_output

# EOF
