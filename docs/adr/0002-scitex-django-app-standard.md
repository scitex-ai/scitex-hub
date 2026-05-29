<!-- ---
!-- Timestamp: 2026-05-30
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/docs/adr/0002-scitex-django-app-standard.md
!-- --- -->

# ADR 0002 — The SciTeX Django "apps and config" standard

- **Status**: Accepted
- **Date**: 2026-05-30
- **Deciders**: ywatanabe (lead), proj-scitex-hub (agent)
- **Affects**: every Django app in the SciTeX ecosystem (`scitex-hub`
  today; `scitex-orochi` and future Django apps next). Enforced by the
  `scitex-dev ecosystem audit-django` auditor (rules `DJ-1xx`–`DJ-5xx`).

## Context

The SciTeX ecosystem already has a shared, well-exercised layout for its
Django apps. `scitex-hub` (formerly `scitex-cloud`, see
[ADR-0001](0001-rename-scitex-cloud-to-scitex-hub.md)) embodies it: a
Django project in `config/`, applications under `apps/`, a split settings
package, and a sibling `src/scitex_<name>/` pip package carrying the
CLI / MCP / skills surface.

Until now this pattern lived only as tribal knowledge in one repo. As we
add more Django apps (`scitex-orochi`), divergence is the default unless
the pattern is written down and machine-checked. This ADR **codifies the
existing `scitex-hub` layout as the canonical standard** — it does *not*
invent a new structure. `scitex-hub` is the reference implementation and
passes the `audit-django` auditor by definition: if a check ever fails on
hub, the check is wrong, not hub.

## Decision

A SciTeX Django app has the following structure, organised into five
sections that map 1:1 onto the `audit-django` rule groups.

### §1 — Django project lives in `config/` (rules DJ-101…DJ-110)

The Django *project* package is `config/` at the repo root, **not**
`<projectname>/`:

```
config/
  __init__.py
  settings/                  # a settings *package*, not a single file
    __init__.py              # environment auto-loader (see below)
    settings_shared.py       # shared base; per-env modules import from it
    settings_dev.py          # development
    settings_staging.py      # staging  (recommended)
    settings_prod.py         # production
    settings_*.py            # optional topic splits (auth, celery, …)
  urls.py                    # ROOT_URLCONF = "config.urls"
  asgi.py                    # ASGI entry point
  wsgi.py                    # WSGI entry point
manage.py                    # at the repo ROOT, defaults to config.settings
```

- `config/settings/__init__.py` is an **environment auto-loader**: it
  dispatches on `SCITEX_<PKG>_ENV` (e.g. `SCITEX_HUB_ENV`) and does
  `from .settings_<env> import *` for development / staging / prod.
- `settings_shared.py` is the shared base every per-env module imports
  from. There is no monolithic `settings.py`.
- `manage.py`, `asgi.py`, `wsgi.py` default `DJANGO_SETTINGS_MODULE` to
  `config.settings` (overridable via `SCITEX_<PKG>_DJANGO_SETTINGS_MODULE`).
- A legacy `<projectname>/settings.py` project package alongside `config/`
  is forbidden (DJ-110).

### §2 — Applications under `apps/` (rules DJ-201…DJ-204)

Django apps live under a top-level `apps/` package, grouped by concern:

```
apps/
  __init__.py
  infra/                     # platform/infrastructure apps
    accounts_app/  auth_app/  organizations_app/  permissions_app/ …
  workspace/                 # end-user workspace apps
    console_app/  docs_app/  repo_app/  figrecipe_app/ …
```

- `apps/` is a Python package (`apps/__init__.py`) so AppConfig `name`s
  resolve as full dotted paths (`apps.workspace.console_app`).
- Each app is a `<name>_app` (or `<name>_api`) directory with an
  `apps.py` declaring an `AppConfig` whose `name` is the full dotted path.

### §3 — Project templates / static (rules DJ-301…DJ-302)

- Global templates (`base.html`, `404.html`, `500.html`, …) live at the
  repo-root `templates/` (added to `TEMPLATES[...]["DIRS"]`).
- Project static *sources* live at the repo-root `static/`
  (`STATICFILES_DIRS`); `collectstatic` targets `staticfiles/`.

### §4 — pip package ↔ Django relationship (rules DJ-401…DJ-402)

- The repo also ships the standard SciTeX **src-layout pip package**
  `src/scitex_<name>/` (CLI, MCP server, skills, SDK) as a **sibling** of
  the Django project.
- `config/` and `apps/` are repo-root siblings of `src/` — the Django
  project is **never nested inside the wheel** (`src/scitex_<name>/config`
  is forbidden), and the pip package is never nested inside the Django
  project. The wheel ships only `src/scitex_<name>/`; the Django runtime
  (`config/`, `apps/`, `templates/`, `static/`) is deployed from the repo.

### §5 — Dependency declaration (rules DJ-501…DJ-502)

- The web/runtime stack (Django, DRF, channels, celery, the SciTeX
  umbrella, …) is declared so the app is installable. **The single
  user-facing install target is the `[all]` extra** (plus `[dev]` for
  tooling).
- **Sub-extras such as `[django]` / `[web]` / `[mcp]` are explicitly
  rejected** (DJ-502). They previously existed and were referenced
  recursively from `[all]` (`scitex-hub[django]`), which deadlocked pip's
  resolver when a recursively-installed dep added a conflicting pin (this
  halted the v0.18.0 release pipeline). Flattening into one `[all]` extra
  eliminates the recursion.
- Version constraints use `>=` floors, not `==` exact pins, for SciTeX
  **umbrella peers** — PS-170's exact-pin rule was deliberately relaxed
  for umbrella peers (scitex-dev, operator-greenlit 2026-05-28) precisely
  because exact pins on co-released umbrella members cause
  `ResolutionImpossible`. Non-peer third-party deps still follow the usual
  floor/pin conventions.

> **Note on the brief that predates this ADR.** Earlier handoff notes
> referred to a `[django]` extra and `==<latest>` PS-170 pins. Both are
> **superseded** by the decisions above (the `[all]`-only flattening and
> the umbrella-peer `>=` relaxation). This ADR documents hub's *actual,
> shipped* policy, which the merged `audit-django` auditor already
> enforces.

## Enforcement

`scitex-dev ecosystem audit-django <distribution>` checks a repo against
this ADR. Rule numbering is `DJ<§><idx>` (e.g. `DJ-101` = §1 rule 01),
mirroring the `PS`/`PA`/`SK` numbering of the sibling auditors. Severity:

- **E (error)** — fails the audit (exit 1): `config/` package, split
  settings package, `settings_shared.py`, `config/urls.py`, `manage.py`,
  `apps/` package, `src/scitex_<name>/` present and not mutually nested,
  Django dependency declared.
- **W (warning)** — reported, non-failing: env-loader `__init__`,
  per-env modules, asgi/wsgi presence, settings-module default, legacy
  project package, `apps/__init__.py`, app dirs / AppConfig presence,
  `templates/` & `static/`, proliferated web sub-extra.

Non-Django packages (no `manage.py` at repo root) are skipped cleanly, so
`audit-all` does not fail on libraries. The auditor is registered in
`scitex-dev` (PR #88) and included in `audit-all`.

## Consequences

**Positive**

- The structure is documented once and machine-checked everywhere; new
  Django apps converge on hub's proven layout instead of diverging.
- `config/` (not `<projectname>/`) removes the confusing
  `scitex_hub.apps.workspace.…` nesting and keeps the deployable Django
  runtime cleanly separate from the shippable pip wheel.
- The `[all]`-only extra policy is now a written rule, not a scar from a
  release-pipeline incident.

**Negative / cost**

- Apps that predate the standard (e.g. `scitex-orochi`) need migration
  work to pass the auditor; until then they will report `DJ-*` findings.
- The standard is opinionated (config/, apps/infra + apps/workspace,
  `[all]` only). New apps must follow it rather than Django's vanilla
  `startproject` layout.

## Alternatives considered

1. **Leave the pattern as tribal knowledge.** Rejected — guarantees
   drift as the number of Django apps grows; nothing catches regressions.
2. **Vanilla Django `startproject` layout (`<projectname>/settings.py`).**
   Rejected — couples the deployable Django project to the wheel package
   name and reintroduces the nesting ADR-0001 removed.
3. **Keep per-feature install sub-extras (`[django]`, `[mcp]`, …).**
   Rejected — the recursive `[all] -> [django]` reference is exactly what
   deadlocked pip's resolver in the v0.18.0 release; DJ-502 now forbids it.

## References

- [ADR-0001](0001-rename-scitex-cloud-to-scitex-hub.md) — the
  `scitex-cloud` → `scitex-hub` rename (hard cutover).
- `scitex-dev` `_cli/audit/_django/` (`_audit.py`, `_checks.py`) — the
  auditor that enforces this ADR; PR #88
  (`feat(ecosystem): add audit-django auditor`).
- `scitex-hub` `config/`, `apps/`, `pyproject.toml [all]` — the reference
  implementation.
- `~/proj/scitex-python/GITIGNORED/SOC.md` — Django apps are L4/L5
  consumers; STX-I008 forbids importing peers' private `_submodules`.

<!-- EOF -->
