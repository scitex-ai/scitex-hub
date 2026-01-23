# SciTeX Scholar Search Configuration Guide

## Configuration Architecture

SciTeX Cloud uses a **two-layer configuration approach**:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Environment Variables (dotenv files)          │
│  - Environment-specific overrides                        │
│  - Can be changed without code deployment               │
│  - Located in: deployment/dotenvs/                      │
└────────────────┬────────────────────────────────────────┘
                 │ overrides
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Django Settings (settings.py)                 │
│  - Sensible defaults                                     │
│  - Fallback values                                       │
│  - Located in: config/settings/settings_shared.py       │
└─────────────────────────────────────────────────────────┘
```

## Settings Hierarchy (Priority Order)

1. **Environment variables** (highest priority)
2. **Django settings** (fallback defaults)

Example:
```python
# In settings_shared.py
SCITEX_SCHOLAR_MAX_WORKERS = int(os.getenv("SCITEX_SCHOLAR_MAX_WORKERS", "5"))  # Default: 5

# In dotenv_dev
export SCITEX_SCHOLAR_MAX_WORKERS=3  # Override for dev → Will use 3

# In dotenv_prod
export SCITEX_SCHOLAR_MAX_WORKERS=8  # Override for prod → Will use 8
```

## Configuration Options

### SciTeX Search Settings

| Variable | Default | Dev | Prod | Description |
|----------|---------|-----|------|-------------|
| `SCITEX_SCHOLAR_USE_CACHE` | `True` | `True` | `True` | Enable result caching |
| `SCITEX_SCHOLAR_MAX_WORKERS` | `5` | `3` | `8` | Parallel workers |
| `SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE` | `30` | `45` | `30` | Timeout (seconds) |
| `SCITEX_SCHOLAR_ENGINES` | All 5 | 3 engines | All 5 | Which engines to use |
| `SCITEX_SCHOLAR_DEFAULT_MODE` | `parallel` | `single` | `parallel` | Search mode |

### Available Engines

- `CrossRef` - Comprehensive metadata, no rate limit
- `PubMed` - Biomedical papers, 3 req/sec limit
- `Semantic_Scholar` - CS/AI papers, 1 req/sec limit
- `arXiv` - Preprints, 3 req/sec limit
- `OpenAlex` - All fields, no rate limit

## Environment-Specific Configurations

### Development (`dotenv_dev`)

**Philosophy**: Faster iteration, predictable debugging

```bash
export SCITEX_SCHOLAR_USE_CACHE=True
export SCITEX_SCHOLAR_MAX_WORKERS=3              # Lower to avoid rate limits
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=45      # Higher for debugging
export SCITEX_SCHOLAR_ENGINES="CrossRef,PubMed,arXiv"  # Fewer engines
export SCITEX_SCHOLAR_DEFAULT_MODE=single        # Sequential for debugging
```

**Why these settings?**
- ✓ Fewer workers → Less chance of hitting rate limits
- ✓ Higher timeout → See full errors, don't timeout during debugging
- ✓ Fewer engines → Faster tests
- ✓ Single mode → Predictable, sequential behavior

### Production (`dotenv_prod`)

**Philosophy**: Maximum performance, all features

```bash
export SCITEX_SCHOLAR_USE_CACHE=True
export SCITEX_SCHOLAR_MAX_WORKERS=8              # More throughput
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=30      # Standard timeout
export SCITEX_SCHOLAR_ENGINES="CrossRef,PubMed,Semantic_Scholar,arXiv,OpenAlex"
export SCITEX_SCHOLAR_DEFAULT_MODE=parallel      # Fast parallel search
```

**Why these settings?**
- ✓ More workers → Handle more concurrent searches
- ✓ Standard timeout → Don't wait too long for slow engines
- ✓ All engines → Best coverage and accuracy
- ✓ Parallel mode → 2-3x faster

## How to Change Settings

### Option 1: Edit dotenv files (Recommended)

```bash
# Edit environment-specific file
vim /home/ywatanabe/proj/scitex-cloud/deployment/dotenvs/dotenv_dev

# Change setting
export SCITEX_SCHOLAR_MAX_WORKERS=5

# Reload environment
source /home/ywatanabe/proj/scitex-cloud/deployment/dotenvs/dotenv_dev

# Restart Django
./deployment/server/server.sh
```

### Option 2: Runtime override (Temporary)

```bash
# Set for current session only
export SCITEX_SCHOLAR_MAX_WORKERS=10

# Start Django with override
./deployment/server/server.sh
```

### Option 3: Edit Django settings (Not recommended)

Only edit `settings_shared.py` to change **defaults**, not environment-specific values.

```python
# In config/settings/settings_shared.py
SCITEX_SCHOLAR_MAX_WORKERS = int(os.getenv("SCITEX_SCHOLAR_MAX_WORKERS", "5"))  # Change default here
#                                                         ^^^
```

## When to Use Each Approach

### Use dotenv files when:
- ✓ Different values needed per environment (dev/prod)
- ✓ Value might change without code deployment
- ✓ Testing different configurations
- ✓ **Most common case - use this 95% of the time**

### Use settings.py when:
- ✓ Changing default fallback values
- ✓ Adding new configuration options
- ✓ Value should be same across all environments

### Use runtime override when:
- ✓ One-time testing
- ✓ Debugging specific issue
- ✓ Emergency override (don't want to commit change)

## Common Configuration Scenarios

### Scenario 1: Reduce rate limiting errors

```bash
# In dotenv_dev or dotenv_prod
export SCITEX_SCHOLAR_MAX_WORKERS=2              # Fewer parallel requests
export SCITEX_SCHOLAR_DEFAULT_MODE=single        # Sequential mode
export SCITEX_SCHOLAR_ENGINES="CrossRef,OpenAlex"  # Only use unlimited engines
```

### Scenario 2: Speed up searches (have API keys)

```bash
export SCITEX_SCHOLAR_MAX_WORKERS=10             # More parallel requests
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=15      # Shorter timeout
export SCITEX_SCHOLAR_DEFAULT_MODE=parallel      # Fast mode
```

### Scenario 3: Debug why search is slow

```bash
export SCITEX_SCHOLAR_MAX_WORKERS=1              # One at a time
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=120     # Very long timeout
export SCITEX_SCHOLAR_DEFAULT_MODE=single        # Sequential
# Check logs to see which engine is slow
```

### Scenario 4: Only use free/unlimited engines

```bash
export SCITEX_SCHOLAR_ENGINES="CrossRef,OpenAlex"  # No rate limits
export SCITEX_SCHOLAR_MAX_WORKERS=10              # Can go higher
```

## Monitoring & Verification

### Check current settings

```bash
# View all SciTeX environment variables
env | grep SCITEX

# Check what Django is using
python manage.py shell
>>> from django.conf import settings
>>> settings.SCITEX_SCHOLAR_MAX_WORKERS
>>> settings.SCITEX_SCHOLAR_ENGINES
```

### Check via API

```bash
# Get current configuration
curl http://127.0.0.1:8000/scholar/api/search/scitex/capabilities/
```

### View in logs

Django logs will show configuration on startup:
```
INFO: Initialized ScholarPipelineSearchParallel (workers=5)
```

## Performance Tuning Guide

### For Speed (Have good API rate limits)

```bash
SCITEX_SCHOLAR_MAX_WORKERS=10
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=20
SCITEX_SCHOLAR_DEFAULT_MODE=parallel
SCITEX_SCHOLAR_USE_CACHE=True
```

Expected: 1-2 second searches, ~20 searches/second

### For Reliability (Conservative)

```bash
SCITEX_SCHOLAR_MAX_WORKERS=2
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=60
SCITEX_SCHOLAR_DEFAULT_MODE=single
SCITEX_SCHOLAR_ENGINES="CrossRef,OpenAlex"  # Only unlimited
```

Expected: 3-5 second searches, ~5 searches/second, no rate limit errors

### For Development

```bash
SCITEX_SCHOLAR_MAX_WORKERS=1
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=120
SCITEX_SCHOLAR_DEFAULT_MODE=single
SCITEX_SCHOLAR_USE_CACHE=False  # See fresh results
```

Expected: Slow but predictable, easy to debug

## Troubleshooting

### Issue: "Rate limit exceeded"

**Solution**: Reduce workers or switch to unlimited engines
```bash
export SCITEX_SCHOLAR_MAX_WORKERS=2
export SCITEX_SCHOLAR_ENGINES="CrossRef,OpenAlex"
```

### Issue: Searches timing out

**Solution**: Increase timeout or reduce engines
```bash
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=60
export SCITEX_SCHOLAR_ENGINES="CrossRef,PubMed"  # Fewer engines
```

### Issue: Settings not taking effect

**Checklist**:
1. ✓ Sourced dotenv file? `source deployment/dotenvs/dotenv_dev`
2. ✓ Restarted Django? `./deployment/server/server.sh`
3. ✓ Check environment: `echo $SCITEX_SCHOLAR_MAX_WORKERS`
4. ✓ Check Django: See monitoring section above

### Issue: Different behavior on server vs local

**Cause**: Different dotenv file loaded

**Solution**: Check which environment is active
```bash
echo $SCITEX_CLOUD_DJANGO_SETTINGS_MODULE
# Should show: config.settings.settings_dev or settings_prod
```

## Best Practices

1. **Always use dotenv files** for environment-specific settings
2. **Never hardcode** API keys or secrets in settings.py
3. **Test changes locally** before deploying to production
4. **Document custom configurations** in this file
5. **Use conservative settings** for production initially
6. **Monitor performance** and adjust based on data

## Files to Edit

### For Development
- `/home/ywatanabe/proj/scitex-cloud/deployment/dotenvs/dotenv_dev`

### For Production
- `/home/ywatanabe/proj/scitex-cloud/deployment/dotenvs/dotenv_prod`

### For Defaults (Rare)
- `/home/ywatanabe/proj/scitex-cloud/config/settings/settings_shared.py`

## Reference: All SciTeX Settings

```python
# In settings_shared.py (with defaults)
SCITEX_SCHOLAR_USE_CACHE = os.getenv("SCITEX_SCHOLAR_USE_CACHE", "True").lower() in ["true", "1", "yes"]
SCITEX_SCHOLAR_MAX_WORKERS = int(os.getenv("SCITEX_SCHOLAR_MAX_WORKERS", "5"))
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = int(os.getenv("SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE", "30"))
SCITEX_SCHOLAR_ENGINES = os.getenv("SCITEX_SCHOLAR_ENGINES", "CrossRef,PubMed,Semantic_Scholar,arXiv,OpenAlex").split(",")
SCITEX_SCHOLAR_DEFAULT_MODE = os.getenv("SCITEX_SCHOLAR_DEFAULT_MODE", "parallel")
```

---

**Last Updated**: 2025-10-22
**Maintainer**: SciTeX Team
