# Agentic Journal — cloud-side thin wrapper

This Django sub-app is a **thin shim** over the standalone package
[`scitex-agentic-journal`](https://github.com/ywatanabe1989/scitex-agentic-journal).

## What this package owns

- Registration into the SciTeX Hub workspace (`apps.py` AppConfig).
- URL include() of the upstream embedded patterns (`urls.py`).
- Hub-side manifest for the app-store loader (`manifest.json`).

## What it does NOT own

- **Logic** — owned by `scitex_agentic_journal._django` upstream.
- **Templates** — owned upstream; the cloud-side wrapper only references
  the upstream `partial_template` via the manifest.
- **Manifest source-of-truth** — the upstream package ships its own
  `_django/manifest.json`. The cloud-side manifest here is the
  hub-app-store record; the AppConfig validates the upstream manifest
  at boot to fail loud if the upstream goes missing.

## Why it exists

- Uniform workspace registration — `apps/workspace/__init__.py` walks
  this directory.
- A natural cut-off if a future hub deploy wants to disable the journal
  surface (remove the wrapper from `INSTALLED_APPS`; no upstream patching
  required).

## Adding behaviour

If you find yourself adding business logic here, **stop**. Push the
logic upstream into `scitex-agentic-journal` and have the wrapper only
re-export. If the upstream surface needs a new entry point, file an
issue on the upstream repo first.

## See also

- Upstream package: https://github.com/ywatanabe1989/scitex-agentic-journal
- ADR-0001 (rename rationale): `docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md`
- Sibling clew_app for the older copy-from-monorepo pattern this wrapper
  intentionally avoids.
