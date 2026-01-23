# Nginx Configuration for SciTeX Cloud

Nginx reverse proxy for SciTeX Django application at `scitex.ai`

---

## Quick Start

### Development
```bash
# Link dev config
sudo ln -sf $(pwd)/scitex_cloud_dev.conf /etc/nginx/sites-enabled/scitex_cloud.conf

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

### Production
```bash
# Link prod config
sudo ln -sf $(pwd)/scitex_cloud_prod.conf /etc/nginx/sites-enabled/scitex_cloud.conf

# Test config
sudo nginx -t

# Get SSL certificate
sudo certbot --nginx -d scitex.ai

# Reload
sudo systemctl reload nginx
```

---

## Architecture

```
Browser → Nginx (80/443) → uWSGI (Unix socket) → Django
                ↓
         Static/Media files (direct serve)
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `scitex_cloud_dev.conf` | HTTP only, for local development |
| `scitex_cloud_prod.conf` | HTTP + HTTPS (unified), for production |
| `nginx.conf` | System-level nginx config (reference) |
| `setup_nginx.sh` | Automated setup script |

**Key Settings:**
- Upstream: Unix socket at `/run/scitex_cloud.sock`
- Static files: `./staticfiles/`
- Media files: `./media/`
- Logs: `./logs/nginx_*.log`

---

## Maintenance

### Check DNS and SSL
```bash
# Check DNS and SSL status
./maintenance/nginx_check_dns.sh

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Common Operations
```bash
# View nginx logs
sudo tail -f /var/log/nginx/error.log
tail -f logs/nginx_access.log

# Check nginx status
sudo systemctl status nginx

# Renew SSL certificate
sudo certbot renew
```

---

## Troubleshooting

### Bad Gateway (502)
```bash
# Check uWSGI service
sudo systemctl status uwsgi

# Check socket exists and accessible
ls -la /run/scitex_cloud.sock
sudo -u www-data test -r /run/scitex_cloud.sock && echo "OK"

# Restart uWSGI
sudo systemctl restart uwsgi
```

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run
```

### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check permissions
ls -la staticfiles/

# Verify nginx config paths
grep static scitex_cloud_prod.conf
```

---

## Configuration Pattern

**Unified Config Approach:**
- Uses single config file for both HTTP and HTTPS
- Self-signed cert for initial HTTPS block
- Certbot automatically updates SSL certificate paths
- No config switching needed after SSL setup

**Ports:**
- Dev: HTTP on 80 (or custom)
- Prod: HTTP on 80 (redirects to HTTPS), HTTPS on 443

**SSL:**
- Let's Encrypt certificates
- Auto-renewal via certbot
- Certificate location: `/etc/letsencrypt/live/scitex.ai/`

---

## Files Structure

```
deployment/nginx/
├── README.md                 # This file
├── scitex_cloud_dev.conf     # Dev config (HTTP)
├── scitex_cloud_prod.conf    # Prod config (unified)
├── nginx.conf                # System config reference
├── setup_nginx.sh            # Setup script
└── maintenance/
    └── nginx_check_dns.sh    # DNS/SSL check tool
```

---

**Status:** Production Ready  
**Domain:** scitex.ai  
**SSL:** Let's Encrypt

<!-- EOF -->
