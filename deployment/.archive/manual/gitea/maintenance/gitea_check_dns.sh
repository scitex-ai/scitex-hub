#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 14:30:00 (ywatanabe)"
# File: ./deployment/gitea/maintenance/gitea_check_dns.sh
#
# SciTeX Cloud - DNS and SSL Check for Gitea
# Checks DNS A record, SSL certificate status, and provides guidance

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_error() { echo -e "${RED}✗ $1${NC}"; }
echo_success() { echo -e "${GREEN}✓ $1${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
echo_info() { echo -e "${BLUE}ℹ $1${NC}"; }
echo_header() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }

# Configuration
DOMAIN="git.scitex.ai"
EXPECTED_IP="162.43.35.139"

# Get actual server IP
echo_header "Server Information"
ACTUAL_IP=$(curl -s ifconfig.me 2> /dev/null || echo "unknown")
if [ "$ACTUAL_IP" = "unknown" ]; then
    echo_warning "Could not detect server IP"
    echo_info "Please check internet connection"
else
    echo_success "Server IP: $ACTUAL_IP"
fi

# Check DNS A Record
echo_header "DNS A Record Check"
DNS_IP=$(dig +short $DOMAIN A 2> /dev/null | head -n1)

if [ -z "$DNS_IP" ]; then
    echo_error "No DNS A record found for $DOMAIN"
    echo ""
    echo_info "Action Required: Add DNS A record"
    echo "  1. Log into your DNS provider (onamae.com)"
    echo "  2. Add A record:"
    echo "     Type: A"
    echo "     Hostname: git"
    echo "     Value: $ACTUAL_IP"
    echo "     TTL: 3600"
    echo ""
    echo "  3. Wait 5-15 minutes for propagation"
    echo "  4. Re-run this script to verify"
    echo ""
    DNS_OK=false
elif [ "$DNS_IP" != "$EXPECTED_IP" ]; then
    echo_warning "DNS A record found but IP mismatch"
    echo "  Expected: $EXPECTED_IP"
    echo "  Found:    $DNS_IP"
    echo ""
    echo_info "Action Required: Update DNS A record"
    echo "  1. Log into your DNS provider (onamae.com)"
    echo "  2. Update A record to: $ACTUAL_IP"
    echo "  3. Wait 5-15 minutes for propagation"
    echo ""
    DNS_OK=false
else
    echo_success "DNS A record: $DOMAIN → $DNS_IP ✓"
    DNS_OK=true
fi

# Check DNS propagation globally
if [ "$DNS_OK" = true ]; then
    echo_header "DNS Propagation Check"
    echo_info "Checking global DNS propagation..."
    echo "  View detailed propagation: https://www.whatsmydns.net/#A/$DOMAIN"
    echo ""
fi

# Check SSL Certificate
echo_header "SSL Certificate Check"
SSL_CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
SSL_KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

if [ ! -f "$SSL_CERT" ]; then
    echo_warning "SSL certificate not found"
    echo "  Expected: $SSL_CERT"
    echo ""

    if [ "$DNS_OK" = true ]; then
        echo_info "DNS is ready! You can now obtain SSL certificate:"
        echo ""
        echo "  Run the following command:"
        echo "  ${GREEN}sudo certbot --nginx -d $DOMAIN${NC}"
        echo ""
        echo "  Certbot will:"
        echo "  1. Verify DNS points to this server"
        echo "  2. Request certificate from Let's Encrypt"
        echo "  3. Automatically update gitea_prod.conf with SSL paths"
        echo "  4. Set up auto-renewal"
        echo ""
        echo "  After certbot succeeds:"
        echo "  ${GREEN}sudo systemctl reload nginx${NC}"
        echo ""
    else
        echo_error "Cannot obtain SSL certificate yet"
        echo "  Reason: DNS A record not properly configured"
        echo "  Action: Fix DNS first, then run certbot"
        echo ""
    fi
    SSL_OK=false
else
    echo_success "SSL certificate found: $SSL_CERT"

    # Check certificate expiry
    if command -v openssl &> /dev/null; then
        EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$SSL_CERT" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2> /dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$((($EXPIRY_EPOCH - $NOW_EPOCH) / 86400))

        if [ $DAYS_LEFT -lt 0 ]; then
            echo_error "Certificate EXPIRED!"
            echo "  Renew now: sudo certbot renew"
        elif [ $DAYS_LEFT -lt 30 ]; then
            echo_warning "Certificate expires in $DAYS_LEFT days"
            echo "  Renew soon: sudo certbot renew"
        else
            echo_success "Certificate valid for $DAYS_LEFT days"
        fi
        echo "  Expires: $EXPIRY_DATE"
    fi

    SSL_OK=true
fi

# Check Nginx configuration
echo_header "Nginx Configuration Check"
NGINX_CONF="/etc/nginx/sites-available/gitea.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/gitea.conf"

if [ ! -f "$NGINX_CONF" ]; then
    echo_error "Nginx config not found: $NGINX_CONF"
    echo "  Run setup: sudo ./deployment/gitea/setup_gitea.sh -e prod"
    NGINX_OK=false
elif [ ! -L "$NGINX_ENABLED" ]; then
    echo_warning "Nginx config not enabled"
    echo "  Run: sudo ln -sf $NGINX_CONF $NGINX_ENABLED"
    NGINX_OK=false
else
    echo_success "Nginx config: $NGINX_CONF"

    # Test nginx configuration
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        echo_success "Nginx configuration valid"
        NGINX_OK=true
    else
        echo_error "Nginx configuration has errors"
        echo "  Run: sudo nginx -t"
        NGINX_OK=false
    fi
fi

# Check Nginx service
if systemctl is-active --quiet nginx; then
    echo_success "Nginx service: running"
else
    echo_error "Nginx service: not running"
    echo "  Start: sudo systemctl start nginx"
fi

# Check Gitea service
echo_header "Gitea Service Check"
if systemctl is-active --quiet gitea; then
    echo_success "Gitea service: running"

    # Check if accessible locally
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo_success "Gitea responding on port 3000"
    else
        echo_warning "Gitea service running but not responding"
        echo "  Check logs: sudo journalctl -u gitea -n 50"
    fi
else
    echo_error "Gitea service: not running"
    echo "  Start: sudo systemctl start gitea"
    echo "  Check: sudo journalctl -u gitea -n 50"
fi

# Summary
echo_header "Summary"
echo ""

if [ "$DNS_OK" = true ] && [ "$SSL_OK" = true ] && [ "$NGINX_OK" = true ]; then
    echo_success "All checks passed! ✓"
    echo ""
    echo "  Access Gitea:"
    echo "  ${GREEN}https://$DOMAIN${NC}"
    echo ""
    echo "  Next steps:"
    echo "  1. Register first user (becomes admin)"
    echo "  2. Generate API token"
    echo "  3. Update Django environment"
    echo ""
elif [ "$DNS_OK" = true ] && [ "$SSL_OK" = false ]; then
    echo_warning "DNS ready, SSL pending"
    echo ""
    echo "  Next step: Obtain SSL certificate"
    echo "  ${GREEN}sudo certbot --nginx -d $DOMAIN${NC}"
    echo ""
    echo "  Then reload nginx:"
    echo "  ${GREEN}sudo systemctl reload nginx${NC}"
    echo ""
elif [ "$DNS_OK" = false ]; then
    echo_error "DNS not configured"
    echo ""
    echo "  Next step: Configure DNS A record"
    echo "  1. Log into onamae.com"
    echo "  2. Navigate to DNS settings"
    echo "  3. Add A record:"
    echo ""
    echo "     Type: A"
    echo "     Hostname: git"
    echo "     Value: $ACTUAL_IP"
    echo "     TTL: 3600"
    echo ""
    echo "  4. Wait 5-15 minutes for propagation"
    echo "  5. Re-run this script to verify:"
    echo "     ./deployment/gitea/maintenance/gitea_check_dns.sh"
    echo ""
else
    echo_error "Some checks failed"
    echo ""
    echo "  Review the errors above and fix them"
    echo ""
fi

# Deployment workflow
echo_header "Deployment Workflow"
echo ""
echo "  1. Configure DNS (if not done):"
echo "     - Add A record: git → $ACTUAL_IP"
echo "     - Wait for propagation (5-15 minutes)"
echo ""
echo "  2. Run Gitea setup:"
echo "     ${GREEN}sudo ./deployment/gitea/setup_gitea.sh -e prod${NC}"
echo ""
echo "  3. Get SSL certificate:"
echo "     ${GREEN}sudo certbot --nginx -d $DOMAIN${NC}"
echo ""
echo "  4. Access Gitea:"
echo "     ${GREEN}https://$DOMAIN${NC}"
echo ""

# Useful commands
echo_header "Useful Commands"
echo ""
echo "  Check DNS:"
echo "    dig +short $DOMAIN A"
echo ""
echo "  Test nginx config:"
echo "    sudo nginx -t"
echo ""
echo "  Reload nginx:"
echo "    sudo systemctl reload nginx"
echo ""
echo "  Get SSL certificate:"
echo "    sudo certbot --nginx -d $DOMAIN"
echo ""
echo "  Renew SSL certificate:"
echo "    sudo certbot renew"
echo ""
echo "  Check SSL expiry:"
echo "    sudo certbot certificates"
echo ""
echo "  Check Gitea status:"
echo "    sudo systemctl status gitea"
echo ""
echo "  View Gitea logs:"
echo "    sudo journalctl -u gitea -f"
echo ""

# EOF
