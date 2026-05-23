# Visitor System (AppUser Test)

> Also available at: http://127.0.0.1:8000/dev/design/visitor-system/

## Overview

Seamless anonymous visitor access without signup. Pre-allocated visitor accounts rotate through a configurable pool with automatic session management.

## Architecture Flow

1. Browser request detected via User-Agent
2. `VisitorAutoLoginMiddleware` allocates a free slot
3. Visitor gets `visitor-001` through `visitor-004`
4. Each visitor has a pre-created `default-project`
5. 1-hour session with 30-min extensions on activity
6. After expiry: auto-reallocated or shown expiry page

### Fallback Chain

1. **Pool available**: Full access as `visitor-NNN`
2. **Pool exhausted**: Shared `readonly-visitor` (read-only)
3. **DEV mode**: Pool auto-resets when full
4. **Signup**: Work migrated to real account, slot freed

## Pool Configuration

| Parameter | Default | Source |
|-----------|---------|--------|
| Pool Size | `4` | `SCITEX_CLOUD_VISITOR_POOL_SIZE` env var |
| Session Lifetime | `1 hour` | `SESSION_LIFETIME_HOURS` |
| Extension on Activity | `30 min` | `SESSION_EXTENSION_MINUTES` |
| Idle Timeout | `30 min` | `IDLE_TIMEOUT_MINUTES` |
| Visitor CPUs | `2` | SLURM_QUOTAS |
| Visitor Memory | `4 GB` | SLURM_QUOTAS |

## Middleware Stack

### VisitorAutoLoginMiddleware
- Detects real browsers via User-Agent (Mozilla, Chrome, Safari)
- Skips bots, curl, wget, empty UA
- Allocates slot using `select_for_update(skip_locked=True)`
- Race-condition safe via database locking
- Falls back to `readonly-visitor` if pool exhausted

### VisitorExpirationMiddleware
- Checks allocation token on every request
- Auto-reallocates seamlessly when session expires
- Transparent to user (no interruption)
- Falls back to expiration page only if pool is full

## Template Context Flags

Injected into all templates via `visitor_expiration_context()` context processor:

```html
{{ is_visitor }}          <!-- True for visitor-* or readonly-visitor -->
{{ is_readonly }}         <!-- True for readonly-visitor (pool overflow) -->
{{ visitor_expires_at }}  <!-- Expiration timestamp for countdown -->
{{ visitor_username }}    <!-- "visitor-001", "readonly-visitor", etc. -->
{{ visitor_cpus }}        <!-- Resource quota: CPUs -->
{{ visitor_memory_gb }}   <!-- Resource quota: Memory in GB -->
```

### Banner States

| State | Flag | UI |
|-------|------|----|
| Read-Only Mode | `is_readonly = True` | Lock icon, editing disabled |
| Visitor Mode | `is_visitor = True` | Warning: data not saved |
| Registered User | Neither flag set | Normal UI |

## Session Keys & Security

```python
SESSION_KEY_PROJECT_ID = "visitor_project_id"
SESSION_KEY_VISITOR_ID = "visitor_user_id"
SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"

# Allocation uses database locking
VisitorAllocation.objects.filter(
    visitor_number=visitor_num
).select_for_update(skip_locked=True).first()

# Token-based validation prevents session hijacking
allocation_token = secrets.token_urlsafe(32)
```

## Management Commands

```bash
# Create visitor pool (default: 4 slots)
docker exec scitex-hub-dev-django-1 python manage.py create_visitor_pool

# Custom size
docker exec scitex-hub-dev-django-1 python manage.py create_visitor_pool --size 8

# Check pool status
docker exec scitex-hub-dev-django-1 python manage.py create_visitor_pool --status

# Reset pool (when stuck)
docker exec scitex-hub-dev-django-1 python manage.py reset_visitor_pool
```

## Key Files

### Backend
- `apps/project_app/services/visitor_pool/visitor_pool.py`
- `apps/project_app/services/visitor_pool/pool_manager.py`
- `apps/project_app/services/visitor_pool/pool_initialization.py`
- `apps/project_app/middleware.py`
- `apps/project_app/context_processors.py`
- `apps/project_app/models/core.py` (VisitorAllocation)

### Frontend & Templates
- `apps/writer_app/.../demo_banner.html`
- `apps/public_app/.../visitor_pool_full.html`
- `apps/public_app/.../visitor_expired.html`
- `apps/public_app/.../visitor_status.html`
- `apps/public_app/views/status/visitor.py`
- `tests/e2e/test_01_visitor_flow.py`
