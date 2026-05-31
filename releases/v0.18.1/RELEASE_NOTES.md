# v0.18.1 — 2026-06-01

## Headline

Stabilization release for the v0.18.0 `scitex-cloud` → `scitex-hub`
rename. The pytest-matrix release gate is now genuinely green on all of
**py3.11 / py3.12 / py3.13** — the "1442 passed, 43 failed" tail noted
in v0.18.0's verification has been driven to zero with real
root-cause fixes (no skips, no mocks, no silent fallback).

This is the first release where v0.18.x can be deployed to NAS without
the gate-3 caveats. v0.18.0 deployments can upgrade in place: the new
`SCITEX_CLOUD_*` env alias (see below) means existing `.env` files
continue to work with a `DeprecationWarning`.

## What changed

### Test gate — real fixes for the v0.18.0 residuals

| Bucket | What broke | Fix |
|---|---|---|
| `writer_app` migration 0007 | `FieldDoesNotExist: NewCollaborativeEdit ... manuscript` at test-DB setup on SQLite (~170 collection errors) | `RemoveIndex×4` and `AlterUniqueTogether(None)` now run **before** the `RemoveField` / `DeleteModel` (#196) |
| `apps_app` URL routing | `/apps/<name>/` 404 after canonical mount moved to `/apps/store/` | tests follow `/apps/store/` (#203, #205) |
| `workspace_app` registry | "hub" slug stale after `hub_app` → `repo_app` rename; `public_app` double-registered as `tools` | slug is now `home`; duplicate `tools` from `public_app/manifest.json` dropped (#203) |
| `apps_app/finders.py` | `PermissionError` from `Path.is_dir()` not handled | swallowed to match upstream Django's `FileSystemFinder` contract (#203) |
| `accounts.APIKey.key_prefix` | UNIQUE collisions in test fixtures (~3 failures) | prefix widened 14 → 16 chars with `unique=True` (#202, #205) |
| `llm.chat_tts_relay` | Message dropped on `asyncio.new_event_loop()` (~4 failures, `NoneType subscriptable`) | `async_to_sync(group_send)` — canonical channels idiom, real production fix (#206) |
| `project_app.visitor_pool` | `kombu.OperationalError` connecting to `localhost:6379` (~6 failures) | Celery `ALWAYS_EAGER=True` + `BROKER_URL="memory://"` gated on `SCITEX_HUB_USE_SQLITE_DEV` (#208) |
| `scholar_app` | URL routing follow-ups (crossref / pdf / public_search / zotero) | bucket fully migrated to `apps/` standardization (#200) |
| `console_app` config stub | `SHOW_MOTD` missing from leaked `sys.modules` stub, causing collection-order pollution | stub now mirrors the real module (#206) |
| `tests/develop/test_audit.py` | Was `@pytest.mark.e2e`-dodged (silent skip under `-m "not e2e"`) | canonical `skip_rules` approach mirrored from scitex-orochi; runs and PASSES (#206) |
| `tests/conftest.py` e2e-guard | Out-of-tree browser tests escaped the gate | guard covers tests living outside `tests/ui/` (#186) |
| Headless release gate | Browser-launch flags in global `pytest` addopts (~98 errors) | removed (#184) |

### Added

- **`SCITEX_CLOUD_*` env alias** (#177): `config/_env.py` exports
  `getenv_with_legacy_alias` / `require_env_with_legacy_alias`. When the
  canonical `SCITEX_HUB_<X>` is unset and the legacy `SCITEX_CLOUD_<X>`
  is set, the legacy value is returned **and** a `DeprecationWarning`
  is emitted. No silent fallback. One-directional (`HUB` is canonical;
  `CLOUD` is the legacy alias from v0.18.0).
- **`scitex_hub.module` umbrella absorption** (#181): cloud helpers,
  project `_mcp`, and skills absorbed from the `scitex` umbrella so the
  hub stands on its own without the `[hub]` extra at runtime.
- **ADR-0002**: formalises the "scitex django apps and config" app
  standard the gate-3 PRs follow.

### CI

- Auto-merge for green develop PRs (CI-native, `check_suite`-triggered).
- SQLite in the pytest-matrix.
- `pytest-cov` in the `[dev]` extra so Codecov works.
- Quality workflow uses single-package `audit-all` (renamed to
  `scitex-hub`).

### Compatibility

- v0.18.0 → v0.18.1 is **drop-in**. No env-var rename flag day.
- The `SCITEX_CLOUD_*` alias emits a `DeprecationWarning` on every legacy
  hit so you can find them in logs. Rename to `SCITEX_HUB_*` at your
  convenience; the alias will be removed in a future major.
- `pip install scitex-cloud` continues to fail loudly with a pointer to
  `scitex-hub` (unchanged from v0.18.0).

## Upgrade

```bash
pip install -U scitex-hub[all]
# (optional) rename SCITEX_CLOUD_* in .env to SCITEX_HUB_* — see v0.18.0 notes
make ENV=dev restart   # or `make ENV=prod restart` on NAS
```

## Verification

`SCITEX_HUB_USE_SQLITE_DEV=1 pytest tests/ -o addopts="" -m "not e2e"
-p no:randomly`:

- pytest-matrix-on-ubuntu-py3.11 — **green**
- pytest-matrix-on-ubuntu-py3.12 — **green**
- pytest-matrix-on-ubuntu-py3.13 — **green**

The 12-failure tail from the post-#206 baseline (3 accounts, 4
chat_tts_relay, 5 visitor_pool) is fully resolved by #205, #206 (TTS
event-loop), and #208 (Celery eager). No skips were added to reach
green.

## Acknowledgements

Iteration was multi-agent (one foreground human operator, several
background Claude agents for rebase + green-up work). The full
audit-trail is in commit messages and PR bodies — every fix is
explicit, scoped, and reversible.
