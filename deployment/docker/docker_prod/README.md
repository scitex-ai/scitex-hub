# Production Deployment

Home server with Cloudflare Tunnel (no port forwarding needed).

## Quick Start

```bash
make ENV=prodstart    # Start all services
make ENV=prodstatus   # Check status
make ENV=prodlogs     # View logs
make ENV=prodrestart  # Restart services
make ENV=prodrebuild  # Full rebuild (causes downtime)
```

## Services & Access

| Service | Local URL | Public URL | Default Credentials |
|---------|-----------|------------|---------------------|
| SciTeX Hub | http://localhost:8000 | https://scitex.ai | - |
| Gitea | http://localhost:3000 | https://gitea.scitex.ai | - |
| CrossRef API | http://localhost:31291 | https://crossref.scitex.ai | - |
| Umami Analytics | http://localhost:3300 | https://umami.scitex.ai | admin / umami |
| Flower (Celery) | http://localhost:5555 | - | - |

## Cloudflare Tunnel Setup

### Prerequisites
1. Cloudflare account with domain (scitex.ai)
2. Cloudflare Zero Trust enabled

### Initial Tunnel Setup
1. Go to https://one.dash.cloudflare.com
2. Navigate to **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Name: `scitex-prod` (or similar)
5. Copy the tunnel token
6. Add to `.env`:
   ```
   SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN_PROD=<your-token>
   ```

### Adding Public Hostnames

For each service, add a public hostname in the tunnel configuration:

#### Main Site (scitex.ai)
- Subdomain: (leave empty)
- Domain: scitex.ai
- Service Type: HTTP
- URL: nginx:80

#### Gitea (gitea.scitex.ai)
- Subdomain: gitea
- Domain: scitex.ai
- Service Type: HTTP
- URL: nginx:80

#### CrossRef API (crossref.scitex.ai)
- Subdomain: crossref
- Domain: scitex.ai
- Service Type: HTTP
- URL: nginx:80

#### Umami Analytics (umami.scitex.ai)
- Subdomain: umami
- Domain: scitex.ai
- Service Type: HTTP
- URL: nginx:80

### Troubleshooting Cloudflare Tunnel

**Tunnel not connecting:**
```bash
docker logs scitex-hub-prod-cloudflared-1
```

**502 Bad Gateway:**
- Check if nginx and django are healthy: `make ENV=prodstatus`
- Check django logs: `docker logs scitex-hub-prod-django-1`

## Umami Analytics Setup

### First-Time Setup
1. Database is auto-created on first start
2. If container fails with "database does not exist":
   ```bash
   docker exec scitex-hub-prod-postgres-1 psql -U scitex_prod -d postgres -c "CREATE DATABASE umami;"
   docker restart scitex-hub-prod-umami-1
   ```

### Access & Login
- Local: http://localhost:3300
- Public: https://umami.scitex.ai
- Default login: `admin` / `umami`
- **IMPORTANT: Change password immediately after first login!**

### Adding Website Tracking
1. Login to Umami
2. Go to Settings → Websites → Add website
3. Name: SciTeX Hub
4. Domain: scitex.ai
5. Copy the tracking script and add to your templates

### Environment Variables
```env
SCITEX_HUB_UMAMI_PORT_PROD=3300
SCITEX_HUB_UMAMI_APP_SECRET=<random-secret>
```

## Database Management

### PostgreSQL
```bash
# Connect to postgres
docker exec -it scitex-hub-prod-postgres-1 psql -U scitex_prod -d scitex_hub_prod

# List databases
docker exec scitex-hub-prod-postgres-1 psql -U scitex_prod -d postgres -c "\l"

# Backup
docker exec scitex-hub-prod-postgres-1 pg_dump -U scitex_prod scitex_hub_prod > backup.sql
```

### Redis
```bash
# Check Redis
docker exec scitex-hub-prod-redis-1 redis-cli ping
```

## Common Issues

### Django Unhealthy / 504 Timeout
**Cause:** Often caused by infinite polling from expired visitor sessions.
**Fix:** Deployed in commit aa356a02 - visitor sessions now redirect to /visitor-expired/ instead of reloading.

### Umami "database does not exist"
```bash
docker exec scitex-hub-prod-postgres-1 psql -U scitex_prod -d postgres -c "CREATE DATABASE umami;"
docker restart scitex-hub-prod-umami-1
```

### Services not starting after rebuild
```bash
make ENV=prodstatus  # Check which services are unhealthy
docker logs <container-name>  # Check specific logs
```
