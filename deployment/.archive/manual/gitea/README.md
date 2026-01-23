<!-- ---
!-- Timestamp: 2025-10-20 18:34:09
!-- Author: ywatanabe
!-- File: /ssh:scitex:/home/ywatanabe/proj/scitex-cloud/deployment/gitea/README.md
!-- --- -->

# Gitea Deployment for SciTeX Cloud

Git hosting service integrated with Django at `git.scitex.ai`

---

## Quick Start

### Development
```bash
# Start Gitea dev container
docker-compose -f docker-compose.gitea-dev.yml up -d

# Access at http://localhost:3001
```

### Production
```bash
# 1. Setup Gitea (one-time)
sudo ./setup_gitea.sh -e prod

# 2. Get SSL certificate (requires DNS A record: git.scitex.ai → server_ip)
sudo certbot --nginx -d git.scitex.ai

# 3. Access at https://git.scitex.ai
```

---

## Prerequisites

**Development:**
- Docker and Docker Compose
- Port 3001 available

**Production:**
- PostgreSQL running (`systemctl status postgresql`)
- Nginx installed
- DNS A record: `git.scitex.ai → your_server_ip`
- Port 3000 (Gitea), 2222 (SSH), 443/80 (HTTPS/HTTP) available

---

## Configuration Files

| File | Purpose |
|------|---------|
| `setup_gitea.sh` | Automated setup script (dev/prod) |
| `gitea_dev.conf` | Nginx config for development |
| `gitea_prod.conf` | Nginx config for production (unified HTTP+HTTPS) |
| `docker-compose.gitea-dev.yml` | Dev container configuration |

**Key Directories:**
- Config: `/etc/gitea/app_{dev,prod}.ini`
- Data: `/var/lib/gitea/data/`
- Logs: `/var/lib/gitea/log/`
- Repositories: `/var/lib/gitea/data/gitea-repositories/`

---

## Maintenance

### Check DNS and SSL Status
```bash
# For Gitea
./maintenance/gitea_check_dns.sh

# Check service status
sudo systemctl status gitea

# View logs
sudo journalctl -u gitea -f
```

### Common Operations
```bash
# Restart service
sudo systemctl restart gitea

# Reload nginx
sudo systemctl reload nginx

# Renew SSL certificate
sudo certbot renew

# Backup database
sudo -u postgres pg_dump gitea_prod > backup_$(date +%Y%m%d).sql
```

---

## Django Integration

**1. Register first user (becomes admin):**
- Open https://git.scitex.ai
- Register with desired credentials
- First user gets admin privileges automatically

**2. Generate API token:**
- Login → Settings → Applications
- "Manage Access Tokens" → "Generate New Token"
- Name: `Django Integration`
- Scopes: `repo`, `admin:org`, `user`
- Copy token (shown only once!)

**3. Update Django environment:**
```bash
vim /home/ywatanabe/proj/scitex-cloud/deployment/dotenvs/dotenv.prod
# Add: export SCITEX_CLOUD_GITEA_TOKEN="your-token"

# Reload
source deployment/dotenvs/dotenv.prod
./scripts/server/scitex_server.sh restart -m prod
```

---

## Architecture

**Nginx Pattern:**
- Uses unified config (`gitea_prod.conf`) for both HTTP and HTTPS
- Self-signed cert for initial HTTPS block
- Certbot automatically updates SSL certificate paths
- No need to switch configs after SSL setup

**Database:**
- Dev: `gitea_dev` (PostgreSQL)
- Prod: `gitea_prod` (PostgreSQL)
- Passwords stored in: `/root/.gitea_{dev,prod}_db_password`

**Ports:**
- Dev HTTP: 3001
- Dev SSH: 2223
- Prod HTTP: 3000 (behind nginx)
- Prod SSH: 2222

---

## Troubleshooting

### Gitea not starting
```bash
sudo journalctl -u gitea -n 50
sudo systemctl restart gitea
```

### SSL certificate issues
```bash
# Check certificate
sudo certbot certificates

# Renew
sudo certbot renew --dry-run
```

### Database connection issues
```bash
# Verify database exists
sudo -u postgres psql -l | grep gitea

# Check password file
sudo cat /root/.gitea_prod_db_password
```

### Nginx configuration errors
```bash
# Test config
sudo nginx -t

# Check symlinks
ls -la /etc/nginx/sites-enabled/gitea.conf
```

---

## Access Points

| Environment | Web UI | SSH Port |
|-------------|--------|----------|
| **Development** | http://localhost:3001 | 2223 |
| **Production** | https://git.scitex.ai | 2222 |

**Clone URLs:**
```bash
# Production HTTPS
git clone https://git.scitex.ai/username/repo.git

# Production SSH
git clone ssh://git@git.scitex.ai:2222/username/repo.git
```

---

## Files Structure

```
deployment/gitea/
├── README.md                    # This file
├── setup_gitea.sh              # Setup script (dev/prod)
├── gitea_dev.conf              # Dev nginx config
├── gitea_prod.conf             # Prod nginx config (unified)
├── docker-compose.gitea-dev.yml # Dev container
├── maintenance/
│   └── gitea_check_dns.sh      # DNS/SSL check tool
└── archive/                     # Old documentation
```

## 127.0.0.1:3001 not working?
The reason 127.0.0.1:3001 doesn't work but 172.19.33.56:3001 does is because Gitea is listening only on IPv6 (:::3001).

``` bash
# 1. Edit the Gitea configuration
sudo nano /etc/gitea/app_dev.ini

# # 2. Find the [server] section and add this line after HTTP_PORT:
# HTTP_ADDR = 0.0.0.0
#  
# # It should look like:
# # [server]
# # APP_NAME = SciTeX Git Hosting (dev)
# # DOMAIN = localhost
# # SSH_DOMAIN = localhost
# # HTTP_PORT = 3001
# # HTTP_ADDR = 0.0.0.0    # <-- Add this line
# # ROOT_URL = http://localhost:3001/
# # ...

sudo systemctl restart gitea_dev
```

## git clone 
git clone ssh://git@localhost:2223/username/repo.git
- Port 8000 = Django (not Gitea)
- Port 3001 = Gitea HTTP
- Port 2223 = Gitea SSH ✅ (this is what you want for git clone)




---

**Version:** 1.21.5  
**Status:** Production Ready  
**Deployed:** 2025-10-20

<!-- EOF -->