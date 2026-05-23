# Citation Graph Service - Configuration Guide

## Quick Start

### 1. Install scitex-code Package

The citation graph service depends on the `scitex.scholar.citation_graph` module from scitex-code.

```bash
# Install in development mode
cd ~/proj/scitex-code
pip install -e .
```

### 2. Configure Database Path

Add to your Django `settings.py`:

```python
# CrossRef Citation Database
CROSSREF_DB_PATH = '/home/ywatanabe/proj/crossref_local/data/crossref.db'
```

Or use environment variable:

```bash
export CROSSREF_DB_PATH=/home/ywatanabe/proj/crossref_local/data/crossref.db
```

### 3. Verify Installation

```bash
# Check health
curl http://localhost:8000/api/scholar/citation-graph/health/
```

Expected response:
```json
{
  "status": "healthy",
  "database": "/home/ywatanabe/proj/crossref_local/data/crossref.db",
  "database_accessible": true
}
```

---

## Configuration Options

### Django Settings

```python
# settings.py

# CrossRef database path (required)
CROSSREF_DB_PATH = os.getenv(
    'CROSSREF_DB_PATH',
    '/home/ywatanabe/proj/crossref_local/data/crossref.db'
)

# Cache backend (recommended: Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'scitex',
        'TIMEOUT': 3600,  # 1 hour default
    }
}

# Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '50/hour',  # For citation graph endpoints
        'user': '200/hour'
    }
}
```

---

## Environment Variables

Create `.env` file:

```bash
# CrossRef Database
CROSSREF_DB_PATH=/home/ywatanabe/proj/crossref_local/data/crossref.db

# Redis Cache (optional but recommended)
REDIS_URL=redis://localhost:6379/1

# Django Settings
DJANGO_SETTINGS_MODULE=scitex_hub.settings.production
```

---

## Database Requirements

### CrossRef SQLite Database

The service requires a local CrossRef database with:

**Required Tables:**
- `works` - Paper metadata
- `citations` - Citation relationships (citing_doi, cited_doi, citing_year)

**Required Indexes:**
```sql
CREATE INDEX idx_citations_cited ON citations(cited_doi, citing_year);
CREATE INDEX idx_citations_citing ON citations(citing_doi);
CREATE INDEX idx_doi_lookup ON works(doi);
```

**Size:** ~1.2TB (47M+ citations)

### Database Location

Default locations checked:
1. `settings.CROSSREF_DB_PATH`
2. Environment variable `CROSSREF_DB_PATH`
3. Fallback: `~/proj/crossref_local/data/crossref.db`

---

## Performance Optimization

### 1. Enable Redis Caching

Install Redis:
```bash
sudo apt-get install redis-server
pip install django-redis
```

Configure in settings.py:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### 2. Database Indexes

Ensure these indexes exist on your CrossRef database:

```sql
-- Check existing indexes
SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='citations';

-- Add if missing
CREATE INDEX IF NOT EXISTS idx_citations_composite
ON citations(citing_doi, cited_doi, citing_year);
```

### 3. Batch Processing

For multiple requests, use batch endpoints or cache aggressively:

```python
# In your application
from django.core.cache import cache

def get_multiple_networks(dois):
    """Get networks for multiple DOIs efficiently."""
    results = {}
    for doi in dois:
        cache_key = f"network:{doi}"
        cached = cache.get(cache_key)
        if cached:
            results[doi] = cached
        else:
            # Fetch and cache
            network = build_network(doi)
            cache.set(cache_key, network, 3600)
            results[doi] = network
    return results
```

---

## Troubleshooting

### Service Unavailable (503)

**Error:** "Citation graph service unavailable - database not configured"

**Solutions:**
1. Check database path:
   ```bash
   ls -lh ~/proj/crossref_local/data/crossref.db
   ```
2. Verify settings:
   ```python
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.CROSSREF_DB_PATH)
   ```
3. Check file permissions:
   ```bash
   chmod 644 ~/proj/crossref_local/data/crossref.db
   ```

### Import Error

**Error:** "ModuleNotFoundError: No module named 'scitex.scholar.citation_graph'"

**Solutions:**
1. Install scitex-code:
   ```bash
   cd ~/proj/scitex-code
   pip install -e .
   ```
2. Verify installation:
   ```bash
   python -c "from scitex.scholar.citation_graph import CitationGraphBuilder; print('OK')"
   ```

### Slow Performance

**Symptom:** Requests taking >60 seconds

**Solutions:**
1. Enable caching (see above)
2. Reduce `top_n` parameter (use 10-20 instead of 50)
3. Check database indexes
4. Consider database on SSD/NVMe storage

### Memory Issues

**Symptom:** Out of memory errors

**Solutions:**
1. Reduce batch sizes in service.py
2. Enable pagination for large result sets
3. Increase server memory
4. Use connection pooling

---

## Monitoring

### Health Check

Regular health monitoring:

```bash
# Cron job every 5 minutes
*/5 * * * * curl -s http://localhost:8000/api/scholar/citation-graph/health/ | jq .status
```

### Logging

Enable detailed logging:

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/citation_graph.log',
        },
    },
    'loggers': {
        'scholar_app.services.citation_graph': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### Metrics

Track these metrics:
- Request count per endpoint
- Average response time
- Cache hit rate
- Error rate
- Database query time

---

## Production Deployment

### Docker

```dockerfile
FROM python:3.11

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install scitex-code
RUN pip install -e git+https://github.com/yourorg/scitex-code.git#egg=scitex

# Copy application
COPY . /app
WORKDIR /app

# Environment
ENV CROSSREF_DB_PATH=/data/crossref.db
ENV DJANGO_SETTINGS_MODULE=scitex_hub.settings.production

CMD ["gunicorn", "scitex_hub.wsgi:application"]
```

### systemd Service

```ini
[Unit]
Description=SciTeX Citation Graph Service
After=network.target redis.service

[Service]
Type=notify
User=scitex
WorkingDirectory=/opt/scitex-hub
Environment="CROSSREF_DB_PATH=/data/crossref.db"
ExecStart=/opt/scitex-hub/venv/bin/gunicorn scitex_hub.wsgi:application

[Install]
WantedBy=multi-user.target
```

---

## Security

### API Keys (Future)

```python
# For authenticated access
from rest_framework.authentication import TokenAuthentication

class CitationGraphAuthenticated(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

### Rate Limiting

Current limits:
- Anonymous: 50 requests/hour
- Authenticated: 200 requests/hour (future)

Adjust in settings.py:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Increase if needed
    }
}
```

---

## Support

For issues:
1. Check logs: `logs/citation_graph.log`
2. Test health endpoint
3. Verify database access
4. Check GitHub issues: https://github.com/yourorg/scitex-hub/issues
