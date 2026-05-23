# Cloudflare Cache Purge

## Overview

SciTeX Hub uses Cloudflare as a CDN with aggressive caching for static files (30-day TTL). When static assets (CSS, JS, images) are updated, the Cloudflare cache must be purged to serve fresh content.

## Configuration

### Required Environment Variables

Add to `deployment/docker/docker_prod/.env`:

```bash
CLOUDFLARE_ZONE_ID=d075a7ed6e3b3b00ec931124c4b09509
CLOUDFLARE_API_TOKEN=<your-api-token>
CLOUDFLARE_DOMAIN=scitex.ai
```

### Getting Credentials

1. **Zone ID**: Cloudflare Dashboard → scitex.ai → Overview → API section (right sidebar)
2. **API Token**:
   - Cloudflare Dashboard → My Profile → API Tokens → Create Token
   - Required permissions: **Zone - Cache Purge - Purge**
   - Zone Resources: **Include - Specific zone - scitex.ai**

## Usage

### Makefile Commands

```bash
# From deployment/docker/docker_prod/
make cache-purge          # Purge common static files
make cache-purge-static   # Same as above
make cache-purge-all      # Purge entire Cloudflare cache

# Or from project root
make -C deployment/docker/docker_prod cache-purge-all
```

### Automatic Purge

Cache purge is automatically included in the rebuild workflow:

```bash
make rebuild  # Includes: down → clean-static → build → up → migrate → collectstatic → cache-purge-static
```

### Script Direct Usage

```bash
# From deployment/docker/common/scripts/
./cloudflare_cache_purge.sh all                    # Purge everything
./cloudflare_cache_purge.sh static                 # Purge common static files
./cloudflare_cache_purge.sh urls "url1 url2 ..."   # Purge specific URLs
```

## Manual Purge Options

### Option 1: Cloudflare Dashboard

1. Go to https://dash.cloudflare.com
2. Select scitex.ai domain
3. Navigate to: **Caching** → **Configuration**
4. Click **Custom Purge** or **Purge Everything**

### Option 2: Direct API Call

```bash
# Purge specific file
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://scitex.ai/static/shared/css/base.css"]}'

# Purge everything
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

## Verification

After purging, verify fresh content is served:

```bash
# Check cache status (should be MISS on first request after purge)
curl -sI "https://scitex.ai/static/shared/css/base.css" | grep -i cf-cache-status

# Check last-modified header
curl -sI "https://scitex.ai/static/shared/css/base.css" | grep -i last-modified
```

## Static Files Purged by Default

The `static` mode purges these common files:

- `/static/shared/css/components/cookie-consent.css`
- `/static/shared/css/base.css`
- `/static/shared/css/components/navbar.css`
- `/static/shared/css/components/footer.css`
- `/static/public_app/css/home.css`
- `/static/vite/main.js`

## Troubleshooting

### Credentials Not Configured

```
Error: Cloudflare credentials not configured
```

Ensure `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` are set in `.env`.

### Invalid Zone ID

```
Could not route to /zones/.../purge_cache
```

Verify Zone ID matches the value in Cloudflare Dashboard → Overview → API section.

### Token Permission Denied

```
Authentication error
```

Ensure API token has **Cache Purge** permission for the scitex.ai zone.

## Related Files

- Script: `deployment/docker/common/scripts/cloudflare_cache_purge.sh`
- Makefile: `deployment/docker/docker_prod/Makefile` (cache-purge targets)
- Config: `deployment/docker/docker_prod/.env` (credentials)

## Why Caching is Aggressive

The nginx config sets:
```nginx
expires 30d;
add_header Cache-Control "public, immutable";
```

This maximizes CDN efficiency but requires manual purge on updates.

---
*Last updated: 2026-01-28*
