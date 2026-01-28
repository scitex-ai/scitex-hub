# Cloudflare Cache Purge Required

## Issue
The cookie consent banner CSS is not displaying correctly on production (scitex.ai).
The banner appears transparent/unstyled because Cloudflare is serving a cached OLD version of the CSS.

## Evidence
- **Cached version date**: Fri, 23 Jan 2026 10:57:04 GMT
- **Current version date**: Tue, 28 Jan 2026 00:35 (in container)
- **Cache status**: HIT (age: ~11+ hours)

## Files to Purge
```
https://scitex.ai/static/shared/css/components/cookie-consent.css
```

## How to Purge

### Option 1: Cloudflare Dashboard
1. Go to https://dash.cloudflare.com
2. Select the scitex.ai domain
3. Navigate to: **Caching** → **Configuration**
4. Click **Custom Purge**
5. Enter URL: `https://scitex.ai/static/shared/css/components/cookie-consent.css`
6. Click **Purge**

### Option 2: Cloudflare API (if configured)
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://scitex.ai/static/shared/css/components/cookie-consent.css"]}'
```

### Option 3: Purge All Cache (if unsure)
In Cloudflare Dashboard: **Caching** → **Configuration** → **Purge Everything**

## Verification
After purging, verify the fix:
```bash
# Check last-modified header (should show Jan 28)
curl -sI "https://scitex.ai/static/shared/css/components/cookie-consent.css" | grep -i last-modified

# Check content has new styles (should show "linear-gradient")
curl -s "https://scitex.ai/static/shared/css/components/cookie-consent.css" | head -15
```

Expected output after purge:
- `last-modified`: should be `Tue, 28 Jan 2026` or later
- CSS should contain: `background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)`

## Root Cause
The nginx config sets aggressive caching:
```
expires 30d;
add_header Cache-Control "public, immutable";
```

This tells Cloudflare to cache static files for 30 days. When CSS is updated, the cache must be manually purged.

## Prevention (Future)
Consider adding cache-busting query strings or hashes to static file URLs when deploying updates.

---
*Created: 2026-01-28 by Claude Code*
