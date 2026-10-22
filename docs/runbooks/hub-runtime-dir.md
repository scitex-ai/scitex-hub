# `runtime/`

Per-host, per-run state for the `hub` package (SciTeX Hub itself): logs,
PID files, caches, ephemeral databases, workspace dirs. Everything here is
regenerable from config + source — never commit anything except this
README and the sibling `.gitkeep`.

`logs/` holds the Django/Celery `RotatingFileHandler` output
(`django.log`, `celery.log`, `errors.log`, etc. — see
`config/settings/settings_logging.py`). The directory is created lazily
by `scitex_config._ecosystem.local_state.runtime_path("hub", "logs")` on
every settings import, so it can never again silently point at a
directory nothing prepared (see incident
`hub-prod-outage-celery-log-permission`, 2026-07-09/10).

Layout reference: scitex-dev skill
`general/01_ecosystem/13_runtime-state-db-layout.md` +
`12_local-state-resolution.md`.
