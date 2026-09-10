<!-- ---
!-- Timestamp: 2026-05-29
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/docs/adr/0002-scitex-django-app-standard.md
!-- --- -->

# ADR 0002 — SciTeX Django App Standard ("apps and config")

- **Status**: Accepted
- **Amended**: 2026-09-10 (Amendment 1 — the Django settings do not import
  the umbrella; §5 and §6 corrected. Measurement and merge order in the
  amendment.)
- **Date**: 2026-05-29
- **Deciders**: ywatanabe (lead), proj-scitex-hub (agent)
- **Affects**: every SciTeX package that ships a Django application
  (today: `scitex-hub`, `scitex-orochi`); the `scitex-dev ecosystem
  audit-django` auditor; downstream Django apps added later.

## Context

SciTeX has more than one Django application in the ecosystem
(`scitex-hub`, `scitex-orochi`, and more to come). They were each laid
out differently — different project-package names, different settings
organization, different relationships between the pip package and the
Django project. That divergence makes it hard for an agent (or a human)
to move between repos, and impossible to write a single auditor that
keeps them honest.

`scitex-hub` already embodies a clean, battle-tested layout: the Django
project lives in `config/`, the apps live under `apps/` (grouped into
`apps/infra/` and `apps/workspace/`), and the pip-installable surface
lives in `src/scitex_hub/`. Rather than invent a new standard, this ADR
**codifies hub's existing layout as the canonical "apps and config"
pattern** for all SciTeX Django apps. hub is the reference
implementation: by definition it conforms, and the auditor uses it as
the fixture that defines "green."

This ADR documents *what is actually in hub today* (verified
2026-05-29), not an aspirational design.

## Decision

Every SciTeX Django app SHALL follow the "apps and config" layout below.
The pip package keeps the standard SciTeX `src/scitex_<name>/` layout
(unchanged from the non-Django package convention); the Django project
is layered on top.

### 1. Django project lives in `config/`

The Django project package is named **`config/`** at the repo root
(never `<projectname>/`). It contains:

- `config/settings/` — a **settings package** (not a single
  `settings.py`), with:
  - `__init__.py` — an **environment auto-loader**. It reads
    `SCITEX_<PKG>_ENV` (e.g. `SCITEX_HUB_ENV`) and `from .settings_<env>
    import *` for `development` / `staging` / `prod`, defaulting to
    development.
  - `settings_shared.py` — base settings shared across environments
    (`BASE_DIR`, `INSTALLED_APPS`, `MIDDLEWARE`, `ROOT_URLCONF`,
    `TEMPLATES`, static/media config, app discovery).
  - `settings_dev.py`, `settings_staging.py`, `settings_prod.py` — one
    module per environment, each `from .settings_shared import *` then
    overriding.
  - Optional focused sub-modules (`settings_auth.py`,
    `settings_celery.py`, `settings_logging.py`,
    `settings_integrations.py`, `quotas.py`, …) imported by the shared
    module — split by concern so no single settings file is monolithic.
- `config/urls.py` — the root URLconf (`ROOT_URLCONF = "config.urls"`).
  May be split into focused includes (`urls_api.py`, `urls_helpers.py`,
  `urls_legacy_redirects.py`).
- `config/asgi.py` and `config/wsgi.py` — entry points. Each resolves
  the settings module from `SCITEX_<PKG>_DJANGO_SETTINGS_MODULE` with a
  fallback to `"config.settings"`, then
  `os.environ.setdefault("DJANGO_SETTINGS_MODULE", …)`.
- `config/routing.py` — Channels routing when the app uses websockets.
- Cross-cutting project glue may also live here (`middleware.py`,
  `context_processors.py`, `branding.py`, `logging_config.py`,
  `celery_app.py`).

`manage.py` stays at the **repo root** and defaults
`DJANGO_SETTINGS_MODULE` to `config.settings` (overridable via
`SCITEX_<PKG>_DJANGO_SETTINGS_MODULE`).

### 2. Apps live under `apps/`

Django apps live under a top-level **`apps/`** package (`apps/__init__.py`
present), grouped into layer sub-packages:

- `apps/infra/` — infrastructure / platform apps (auth, accounts,
  organizations, permissions, project, search, integrations, …).
- `apps/workspace/` — user-facing workspace apps (the app-store / shell
  apps: repo, docs, scholar, writer, tools, console, …).

Each app is a directory named **`<name>_app`** (or `<name>_api` for
API-only apps) containing at minimum an `apps.py` with an `AppConfig`
whose `name` is the **full dotted path**
(e.g. `name = "apps.workspace.repo_app"`). Typical app internals:
`apps.py`, `urls/`, `views/`, `templates/`, `static/`, plus
`models.py`/`models/`, `migrations/`, `manifest.json`, `skill.py` as
needed.

`INSTALLED_APPS` is assembled in `settings_shared.py` as
`DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS`, where `LOCAL_APPS` is
**auto-discovered** by walking `apps/infra/` and `apps/workspace/` for
sub-dirs that contain an `apps.py`. Adding an app is therefore just
dropping a directory in — no manual registration.

### 3. Project-level templates and static

Project-wide (non-app) assets live at the repo root:

- `templates/` — global templates (`global_base.html`, `404.html`,
  `500.html`, shared partials). Registered in `TEMPLATES["DIRS"]`.
- `static/` — project static sources; `STATICFILES_DIRS` points here.
  `STATIC_ROOT` is `staticfiles/` (collectstatic target, gitignored).
  App-local static is picked up by Django's `AppDirectoriesFinder`.

### 4. The pip package ↔ Django relationship

The pip-installable package keeps the standard SciTeX layout:
**`src/scitex_<name>/`** with the usual `_cli/`, `_config/`,
`_mcp_tools/`, `_mcp_server.py`, `_skills/`, `__main__.py`, public
`_api.py`. It provides the CLI (`scitex-<name>`), the MCP server
(`scitex-<name>-mcp`), skills, and the SDK — i.e. the *programmatic /
operator* surface. The Django project in `config/` + `apps/` provides
the *web/runtime* surface.

The two are **siblings in one repo**, not nested: the Django project is
NOT inside `src/scitex_<name>/`, and the pip package is NOT inside
`config/`. `[project.scripts]` and `[project.entry-points]` point at the
`src/` package only; Django discovers `config` and `apps` from the repo
root (they are not part of the wheel).

### 5. Dependency declaration

Per the SciTeX umbrella convention, sub-extras are NOT proliferated.
hub deliberately **flattened** its former `[django]`/`[gui]`/`[mcp]`
sub-extras into a single user-facing **`[all]`** extra after recursive
sub-extra references tripped pip's resolver (a recursively-installed dep
added a conflicting pin). The standard is therefore:

- **Core `dependencies`** in `[project]`: only the always-needed runtime
  (CLI, rich/click, the sibling scitex packages the CLI imports).
- **`[all]`**: the full web/runtime stack — Django + DRF + auth + ORM +
  ASGI/Channels + Celery + the rest. This is the single user-facing
  install target (`pip install scitex-<name>[all]`).
- **`[dev]`**: development-only tooling (formatters, linters, dev test
  plugins). CI installs `".[all,dev]"`.
- **`import scitex as stx`** is NOT required by the Django settings.
  **Amended 2026-09-10** — see "Amendment 1" below. The four sites that
  carried it decorated dead `main()` entry points; the decorators were
  removed along with the import, and the settings load without the
  umbrella. The umbrella `scitex>=…` stays in `[all]` for other, measured
  reasons (scholar's `from scitex import logging` and the
  `scitex.scholar.*` pipelines).

Per **PS-170**, peer scitex packages SHOULD be pinned to the current
published version. (hub's core `dependencies` still carry stale `>=`
floors — that is Phase-1 cleanup, out of scope for this ADR; the
auditor flags it as a warning, not an error, so hub stays green.)

### 6. Settings reference the umbrella

**AMENDED 2026-09-10 — the settings do NOT reference the umbrella.** This
section previously read: "`config/settings/settings_shared.py` does
`import scitex as stx` and uses `@stx.session` / `@stx.module`." That was
true in letter and hollow in substance; see "Amendment 1". Django apps
are top-layer (L4/L5) consumers per SOC: they MAY import lower scitex
packages but only via the **public API** (never private `_submodules`,
enforced by linter **STX-I008**).

## Amendment 1 — 2026-09-10: the settings do not require the umbrella

**Amends**: §5 (dependency declaration), §6 (settings reference the umbrella).
**Card**: `hub-settings-import-the-umbrella-for-one-decorator-20260818`.
**Status of the amendment**: proposed with the measurement below; held for
review because two in-flight branches touch the same file (see "Merge order").

### What was measured

The four `import scitex as stx` sites in the settings/routing layer were each
used for exactly one thing:

    config/settings/settings_shared.py:488-489     @stx.session  on a no-op main()
    config/settings/settings_auth.py:156-157       @stx.session  on a no-op main()
    config/settings/settings_integrations.py:184-185  @stx.session on a no-op main()
    config/routing.py:41                           @stx.module   on a no-op main()

Each sat behind `if __name__ == "__main__":` with a docstring saying the module
was not meant to be executed. Django IMPORTS a settings module and never runs
one, so that guard could not fire: the decorators were on dead entry points.
`stx` was used for nothing else in any of the four files.

### Why it mattered

Loading hub's settings therefore required the umbrella, which pins every
sibling exactly (`scitex-ui==0.6.0` among ~40), while hub declares
`scitex-ui>=0.20.0`. Any environment that could import settings had scitex-ui
pinned to 0.6.0 — which made
`tests/config/test_static_manifest.py::test_collectstatic_succeeds_with_hashed_urls`,
the guard on a production build step, structurally unrunnable against the
version hub's own pyproject declares.

### The amendment

Django settings SHALL NOT import the umbrella. The four dead `main()` blocks
and their four `import scitex as stx` lines are deleted, asserted by
`tests/config/test_settings_do_not_require_the_umbrella.py`, which imports the
settings chain in a child interpreter where `scitex` is made unimportable —
with two positive controls (the blocker does block; blocking a package the
settings genuinely need does fail the child).

The umbrella REMAINS a dependency in `[all]`/`[dev]`, and that is measured, not
assumed: 35 runtime files still reach for it, chiefly scholar's
`from scitex import logging` and the `scitex.scholar.*` pipelines. This
amendment removes the SETTINGS requirement; it does not remove the package.

### Merge order

Two open branches edit `config/settings/settings_shared.py` for unrelated
reasons — `feat/retire-visitor-pool-signup-first` (#764) and
`feat/secret-key-fallbacks-for-zero-logout-rotation` (#740). This amendment
lands AFTER them, rebased, so the visitor/auth work is not forced to resolve a
conflict it did not cause. Until then it is preserved on
`fix/settings-do-not-require-the-umbrella` and is not a PR.

## Consequences

**Positive**

- One layout across all SciTeX Django apps; an agent can navigate
  hub and orochi the same way.
- A single auditor (`audit-django`) can enforce the standard; hub is the
  green fixture by construction.
- App discovery is automatic — adding an app is dropping a directory.
- Settings are split by concern and by environment, so no monolithic
  `settings.py`.

**Negative / cost**

- `scitex-orochi` does NOT follow this yet (Django project in `orochi/`,
  not `config/`); it must be migrated (Phase 1, separate handoff).
- The `config/` name is a Django-unusual choice (Django's `startproject`
  uses the project name); contributors coming from vanilla Django must
  learn the convention.

## Alternatives considered

1. **Keep the Django project named after the package
   (`scitex_hub/settings.py`).** Rejected — collides conceptually with
   the `src/scitex_hub/` pip package (two things called `scitex_hub`),
   and is exactly the nesting confusion ADR 0001 already fought.
2. **Single `settings.py` with env branching inside.** Rejected — hub's
   real settings are large and concern-split; a single file would be
   unmaintainable and untestable per-environment.
3. **Invent a fresh standard rather than codify hub.** Rejected by the
   operator directive: hub is the reference; Phase 0 codifies it, does
   not redesign it.
4. **Require a `[django]` extra.** Rejected — hub deliberately removed
   sub-extras to fix a pip resolver deadlock; the canonical install
   target is `[all]`. Requiring `[django]` would make the reference
   implementation fail its own auditor.

## References

- ADR 0001 — Rename `scitex-cloud` to `scitex-hub` (the `config/` vs
  package-name nesting concern originates there).
- `scitex-hub/config/settings/` (the reference settings package).
- `scitex-hub/apps/{infra,workspace}/` (the reference app layout).
- `scitex-hub/pyproject.toml` (`[all]` extra, flattened sub-extras).
- `~/proj/scitex-python/GITIGNORED/SOC.md` (L4/L5 consumer constraint).
- Linter STX-I008 (no private cross-package imports).
- `scitex-dev ecosystem audit-django` (the enforcement auditor).

<!-- EOF -->
