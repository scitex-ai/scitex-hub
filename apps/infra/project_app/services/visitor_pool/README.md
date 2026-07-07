# Visitor Pool

Manages temporary visitor accounts (`visitor-001` to `visitor-004`) for
anonymous users who explore SciTeX without signing up.

## Security invariant

**Only verified-clean slots are redistributed; failed slots are
quarantined.** A slot may be handed to a new visitor only after its
workspace has been wiped, VERIFIED empty, re-cloned from the template,
and the clone verified — since the previous visitor used it. Any
failure anywhere in that pipeline quarantines the slot (never served
again until `manage.py reconcile_visitor_slots` re-cleans and
re-verifies it).

## Pool Lifecycle

```
Container start
    → create_visitor_pool                    # ensure accounts exist
    → reconcile_visitor_slots (entrypoint)   # boot fail-safe:
        every slot quarantined as unverified,
        wipe+verify each; only survivors return to circulation
         ↓
Visitor arrives at a feature page
    → allocate_visitor()
        → slot must be workspace_ready=True AND quarantined=False
        → synchronous template-marker check (safety net)
        → VisitorAllocation activated (DB lock prevents race)
        → session stores allocation_token, visitor_user_id
      (no ready slot → readonly-visitor fallback;
       session["visitor_readonly_reason"] = "no_ready_slot" | "pool_full")
         ↓
Visitor uses the platform for up to 1 hour
         ↓
Slot released (deallocation, expiry middleware, idle sweep, signup claim)
    → release_slot()                         # slot_lifecycle.py
        → is_active=False, workspace_ready=False   (out of circulation NOW)
        → enqueue reset_visitor_slot (Celery)
             → WorkspaceManager.reset_visitor_workspace()
                 1. delete ALL the visitor's Project rows
                 2. wipe filesystem base dir + VERIFY empty
                 3. hard-delete ALL the visitor's Gitea repos + VERIFY zero
                 4. clear user-scoped rows (chat, LLM logs, app installs/
                    stars/reviews, dev installs)
                 5. create fresh Project row
                 6. clone template + VERIFY marker
             → success: workspace_ready=True (back in the pool)
             → ANY failure: slot QUARANTINED (never redistributed)
```

## Why this cannot serve a dirty slot

* **Wipe happens at release, allocation only checks.** Allocation never
  cleans anything inline; it refuses everything that is not
  verified-clean. A Celery outage therefore cannot leak — unreset slots
  just stay out of circulation and overflow goes to `readonly-visitor`.
* **Guarded + verified wipe.** `workspace_wipe.py` recovers from
  permission errors (chmod+retry — the production failure was an
  unguarded `rmtree` aborting on a read-only `revision.tex`) and then
  VERIFIES the directory is empty. The fresh `Project` row is created
  only *after* the verified wipe (previously it was created first, so a
  failed wipe still produced an "initialized" slot with the previous
  visitor's files).
* **Gitea repos are purged with verification.** Visitor repos live at a
  stable path (`visitor-NNN/default-project`) across rotations; a
  surviving repo would be adopted by the next visitor's project. The
  reset lists + deletes every repo the visitor owns and verifies zero
  remain; the `create_gitea_repository` signal additionally refuses
  adoption for visitor-owned projects.
* **Expiry uses the same pipeline.** `VisitorExpirationMiddleware` calls
  `deallocate_visitor()` (release pipeline) instead of just popping
  session keys.
* **Boot fail-safe.** `reconcile_visitor_slots` runs at every service
  start: all slots (allocated / mid-reset / unknown) are quarantined and
  only return after wipe+verify passes. Until at least one slot
  verifies, visitors get `readonly-visitor` with
  `visitor_readonly_reason="no_ready_slot"`.
* **Container state (TODO).** Apptainer/container overlay state is NOT
  yet wiped — scitex-container integration is a follow-up tracked on
  card `hub-visitor-slot-isolation-audit`.

## What Gets Cleared on Reset

`WorkspaceManager.reset_visitor_workspace(user)`:

| Data | Action |
|------|--------|
| `Project` rows (ALL owned by the visitor) | Deleted, then default one re-created from template |
| Project filesystem (entire user base dir) | Guarded wipe + verified empty + `clone_template` + verified marker |
| Gitea repositories (ALL owned by the visitor) | Hard-deleted + verified zero remain |
| `ChatSession` / `LLMUsageLog` | Deleted |
| `ModuleInstallation` / `DevInstallation` / `ModuleStar` / `ModuleReview` | Deleted |
| Container/overlay state | **TODO** — card `hub-visitor-slot-isolation-audit` |

## Key Files

| File | Role |
|------|------|
| `pool_manager.py` | `PoolAllocator`: allocate (ready gate + sync check) / deallocate / status |
| `slot_lifecycle.py` | `release_slot`, `quarantine_slot`, `reset_and_verify_slot` |
| `workspace_manager.py` | `WorkspaceManager`: ordered fail-loud reset pipeline |
| `workspace_wipe.py` | Guarded rmtree (chmod+retry) + verified-empty wipe |
| `pool_initialization.py` | `PoolInitializer`: create accounts on first boot |
| `pool_cleanup.py` | Expired/idle sweep (release pipeline; called by Celery beat) |
| `visitor_pool.py` | `VisitorPool` facade used by views and middleware |
| `../tasks/visitor_workspace_tasks.py` | `reset_visitor_slot` Celery task |

Management commands:

```bash
python manage.py reconcile_visitor_slots            # boot fail-safe / release quarantined slots
python manage.py reconcile_visitor_slots --quarantine-only
python manage.py reconcile_visitor_slots --visitor 2
python manage.py reset_visitor_pool                 # hard reset all slots (same pipeline)
python manage.py reset_visitor_pool --free-expired  # release expired allocations only
python manage.py create_visitor_pool                # create missing accounts/projects
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
# {"total": 4, "allocated": 1, "free": 3, "expired": 0,
#  "quarantined": 0, "ready": 3}
```

From the shell: `make status` shows pool health alongside container health.

## Session Keys

```python
SESSION_KEY_PROJECT_ID        = "visitor_project_id"
SESSION_KEY_VISITOR_ID        = "visitor_user_id"
SESSION_KEY_ALLOCATION_TOKEN  = "visitor_allocation_token"
SESSION_KEY_READONLY_REASON   = "visitor_readonly_reason"
```

The allocation token is a 32-byte `secrets.token_hex()` value stored only
in the visitor's session cookie (HttpOnly, Secure in production).
Visitor accounts have no password and cannot be logged in to directly.
