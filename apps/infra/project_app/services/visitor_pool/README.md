# Visitor Pool

Manages temporary visitor accounts (`visitor-001` to `visitor-004`) for
anonymous users who explore SciTeX without signing up.

## Pool Lifecycle

```
Container start
    → reset_visitor_pool (entrypoint.sh)    # hard reset all slots
    → create_visitor_pool                    # ensure accounts exist
         ↓
Visitor arrives at a feature page
    → allocate_visitor()
        → @ensure_clean_workspace            # safety net before handoff
        → VisitorAllocation created (DB lock prevents race)
        → session stores allocation_token, visitor_user_id
         ↓
Visitor uses the platform for up to 1 hour
         ↓
Session ends (expiry, sign-up, or navigation away)
    → deallocate_visitor()
        → allocation.is_active = False
        → @reset_workspace_after             # immediate cleanup
            → WorkspaceManager.reset_visitor_workspace()
                → Project deleted + re-created from template
                → _clear_visitor_data()      # removes chat/LLM history
```

## 3-Layer Security Model

Data leakage between visitors is prevented at three levels, applied
in order from most-frequent to least-frequent path:

### Layer 1 — `@reset_workspace_after` on `deallocate_visitor()`

Normal deallocation path. After the slot is marked inactive the decorator
calls `WorkspaceManager.reset_visitor_workspace()` unconditionally.

```python
# decorators.py
@reset_workspace_after      # ← applied here
def deallocate_visitor(cls, session): ...
```

### Layer 2 — `@ensure_clean_workspace` on `_try_allocate_slot()`

Safety net for edge cases where Layer 1 did not run: server crash,
Docker restart, idle timeout, or NAS reboot. Checks whether the slot
was previously used and resets it before handing it to the new visitor.

```python
# decorators.py
@ensure_clean_workspace     # ← applied here
def _try_allocate_slot(cls, visitor_num, session, pool_size): ...
```

### Layer 3 — `reset_visitor_pool` in `entrypoint.sh`

Hard reset of **all** slots on every container restart. No state
survives a container bounce.

```bash
# entrypoint.sh (runs in background after gunicorn binds)
python manage.py reset_visitor_pool   # deactivates + workspace-wipes all slots
python manage.py create_visitor_pool  # ensures accounts/projects exist
```

## What Gets Cleared on Reset

`WorkspaceManager.reset_visitor_workspace(user)` deletes and re-creates:

| Data | Action |
|------|--------|
| `Project` (DB row) | Deleted then re-created from template |
| Project filesystem | `shutil.rmtree` + `clone_template(VISITOR_TEMPLATE_ID)` |
| `ChatSession` / `ChatMessage` | Deleted (via `_clear_visitor_data()`) |
| `LLMUsageLog` | Deleted (via `_clear_visitor_data()`) |
| `VisitorAllocation` | Marked `is_active=False` |

## Key Files

| File | Role |
|------|------|
| `decorators.py` | `@reset_workspace_after`, `@ensure_clean_workspace` |
| `pool_manager.py` | `PoolAllocator`: allocate / deallocate / status |
| `workspace_manager.py` | `WorkspaceManager`: reset workspace, clear data |
| `pool_initialization.py` | `PoolInitializer`: create accounts on first boot |
| `pool_cleanup.py` | Expired allocation cleanup (called by Celery beat) |
| `visitor_pool.py` | `VisitorPool` facade used by views and middleware |

Management commands:

```bash
python manage.py reset_visitor_pool             # reset all slots
python manage.py reset_visitor_pool --visitor 2 # reset one slot (partial)
python manage.py reset_visitor_pool --free-expired  # free expired allocations only
python manage.py create_visitor_pool            # create missing accounts/projects
```

## Race Condition Prevention

`_try_allocate_slot()` uses `select_for_update(skip_locked=True)` so
concurrent requests skip already-locked rows rather than blocking.
`IntegrityError` from the `UNIQUE` constraint on `visitor_number` is
caught as a secondary guard.

## Pool Status

```python
from apps.infra.project_app.services.visitor_pool import VisitorPool

status = VisitorPool.get_pool_status()
# {"total": 4, "allocated": 1, "free": 3, "expired": 0}
```

From the shell: `make status` shows pool health alongside container health.

## Session Keys

```python
SESSION_KEY_PROJECT_ID        = "visitor_project_id"
SESSION_KEY_VISITOR_ID        = "visitor_user_id"
SESSION_KEY_ALLOCATION_TOKEN  = "visitor_allocation_token"
```

The allocation token is a 32-byte `secrets.token_hex()` value stored only
in the visitor's session cookie (HttpOnly, Secure in production).
Visitor accounts have no password and cannot be logged in to directly.
