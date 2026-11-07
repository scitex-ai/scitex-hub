# Project scope API (`/api/project/scope/`)

Measured 2026-10-22. Source: `apps/infra/project_app/views/projects/scope_api.py`,
`apps/infra/project_app/services/project_scope.py` (`HubProjectProvider`),
SDK `scitex_sdk.ui.project_scope` (`scoped_project_listing_view`,
`supports_scoped_capability`).

The hub serves the SDK's tagged-scope picker contract. `HubProjectProvider`
offers the optional `ScopedProjectProvider` capability; the view delegates
to the SDK's `scoped_project_listing_view`, so hub and leaf stay on the
same wire shape by construction.

## Contract

- `GET` → `{"projects": [{id, name, detail}], "current": id|null,
  "allow_user_scope": true, "current_scope": "user"|"project"|absent}`
  - `current_scope: "user"` + `current: null` = explicit All selection.
  - `current_scope` omitted + `current: null` = unselected.
  - Stale (inaccessible) stored projects surface as unselected, never as
    a silent fallback to another project.
- `POST {"id": "owner/slug"}` (legacy) → `{"current": id}` (403 if not accessible).
- `POST {"scope": "user", "id": null}` → `{"current": null, "current_scope": "user"}`.
- `POST {"scope": "project", "id": "owner/slug"}` → `{"current": id, "current_scope": "project"}`
  (403 if not accessible).
- Unknown scopes, null ids, and inaccessible projects → 403
  `{"error": "project not accessible"}`. The `user` id key must be present
  with literal null; a missing key is refused like any malformed selection.

## State

The committed selection lives on `UserProfile.last_active_repository`:
a row = `{"scope": "project", id}`, null = explicit-All. `remember_scope`
commits atomically; the two shapes are never stored apart.

## Verification

Live-contract test `tests/apps/project_app/test_scope_api_contract.py`
(5/5 green against container dev) plus tight loop
`~/.hermes/cache/scratch/tightloop_scope.sh` for post-rebuild proof.
DB-backed pytest cannot run here (role lacks CREATEDB).
