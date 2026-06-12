# Live Paper — cloud-side thin wrapper

This Django sub-app is a **thin shim** over the standalone
[`scitex-live-paper`](https://github.com/ywatanabe1989/scitex-live-paper).

## What this package owns

- Registration into the SciTeX Hub workspace (`apps.py` AppConfig).
- URL include of the upstream embedded patterns (`urls.py`).
- Hub-side manifest for the app-store loader (`manifest.json`).

## What it does NOT own

- **Logic** — owned by `scitex_live_paper._django` upstream.
- **Templates / static / handlers** — owned upstream.
- **The plugin-mount contract** (`mount(resolver=...)`) — owned
  upstream; this wrapper currently uses the single-tenant env-pinned
  path. A follow-up PR will flip the wrapper to use
  `mount(resolver=...)` once the upstream `BundleContext` dataclass
  is publicly importable.

## Configuration

The single-tenant path is driven by an env var consumed inside the
container Django process:

```
SCITEX_LIVE_PAPER_BUNDLE=/path/inside/container/to/bundle
```

See `docs/runbooks/local-staging-orochi-cloud.md` for the bring-up
sequence on a local staging workstation. The bundle path is read by
the upstream `_django/urls.py`; the wrapper does not touch it.

## Embedding the viewer in another hub view

The upstream SPA shell honours an **embed-mode** flag that strips its
own chrome so the hub-side host (e.g. a project_app panel rendering
the viewer inside an iframe) can avoid double-chrome:

```html
<iframe src="/apps/live-paper/?embed=1" data-embed-mode="1"></iframe>
```

Both knobs are part of the upstream SPA contract (scitex-live-paper
PR #24, merged):

- `?embed=1` — query-string flag the SPA reads to skip its own
  chrome (nav, headers, footers).
- `data-embed-mode="1"` — attribute the SPA places on the root div;
  hub-side JS that wraps the iframe can read it to suppress hub
  chrome too.

If you mount the viewer **without** the iframe (e.g. as a stand-alone
hub page), drop both flags so the SPA renders its full chrome.

## Adding behaviour

If you find yourself adding business logic here, **stop**. Push the
logic upstream into `scitex-live-paper` and have the wrapper only
re-export.

## See also

- Upstream package: https://github.com/ywatanabe1989/scitex-live-paper
- Sibling wrapper: `apps/workspace/agentic_journal_app/` (same shape).
- Local-staging runbook: `docs/runbooks/local-staging-orochi-cloud.md`.
