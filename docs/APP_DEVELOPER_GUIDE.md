# SciTeX Cloud — App Developer Guide

For AI agents and developers building apps that integrate with scitex-hub.

---

## 1. Platform Overview

SciTeX Cloud renders inside a **three-column workspace layout**:

```
┌─────────────┬──────────────────┬────────────────┐
│  AI Pane    │  Worktree/Files  │  Module (app)  │
└─────────────┴──────────────────┴────────────────┘
```

What the platform provides to each app: workspace frame (tab bar, layout,
resizers), file tree (project directory, mode-filtered), file viewer, AI chat
(with `ai_hint` context), active project context, and platform REST APIs.

Apps provide a **partial template** loaded by AJAX into the module column.
They never render a full HTML page themselves.

---

## 2. App Registration

### manifest.json (schema 2.0.0)

```json
{
  "$schema": "scitex-app-manifest",
  "$schema_version": "2.0.0",
  "name": "my_app",
  "label": "My App",
  "app_name": "my_app",
  "icon": "fas fa-puzzle-piece",
  "description": "Short description.",
  "version": "0.1.0",
  "license": "AGPL-3.0",
  "keyboard_shortcut": "M",
  "order": 60,
  "partial_template": "my_app/index_partial.html",
  "context_builder": "apps.my_app.views.build_my_app_context",
  "ai_hint": "What the LLM sees about this app.",
  "allowed_extensions": [".csv", ".json"],
  "hidden_patterns": ["__pycache__", "node_modules", ".git", ".venv"],
  "privileges": [
    {"type": "filesystem", "scope": "project", "reason": "Read/write data files"}
  ],
  "dependencies": {"python": ["my-lib>=1.0"], "system": [], "node": [], "r": [], "other": []}
}
```

### ModuleConfig fields (Python dataclass)

`name` (slug), `label`, `app_name`, `icon_fa`, `partial_template`,
`context_builder` (dotted path), `order` (tab position), `keyboard_shortcut`,
`ai_hint`, `allowed_extensions`, `privileges`, `default_enabled`, `status`
(`stable|wip|beta|deprecated`), `is_dev`.

### Built-in registration

Add manifest path to `_BUILTIN_MANIFEST_PATHS` in `registry.py`:

```python
_BUILTIN_MANIFEST_PATHS = [
    "workspace/hub_app/manifest.json",
    "workspace/my_app/manifest.json",  # add here
]
```

### External registration (pip-installed apps)

```toml
# pyproject.toml
[project.entry-points."scitex_modules"]
my_app = "my_app:get_module_config"
```

```python
# my_app/__init__.py
from apps.infra.workspace_app.registry import ModuleConfig

def get_module_config() -> ModuleConfig:
    return ModuleConfig(name="my_app", label="My App", app_name="my_app", ...)
```

Discovered automatically at startup via `discover_external_modules()`.

---

## 3. Dev Install Workflow

Personal dev tabs — no approval, only installing user sees the tab.

```http
POST /apps/store/api/dev/install/
{"owner": "alice", "repo": "my-app"}
→ {"success": true, "module_name": "dev__alice__my-app", "label": "My App"}
```

What happens: Gitea access check → `validate_dev_repo()` (needs `templates/`
dir) → reads `manifest.json` → creates `DevInstallation` record. Tab appears
on next page load. Module name is `dev__<owner>__<repo>`.

```http
POST /apps/store/api/dev/<owner>/<repo>/uninstall/   # soft-delete
POST /apps/store/api/dev/<owner>/<repo>/reinstall/   # re-enable
GET  /apps/store/api/dev/url/?project_id=<repo>      # get workspace URL
```

---

## 4. Platform Services (REST APIs)

Base: `/platform/api/`. Session auth required. Send `X-CSRFToken` for writes.

### DataStore — structured records per app

```
GET|POST  /platform/api/data/<app>/<schema>/           list / create
GET|PUT|DELETE  /platform/api/data/<app>/<schema>/<uuid>/
POST      /platform/api/data/<app>/<schema>/search/    filter
```

### FileVault — file storage scoped to app

```
GET    /platform/api/files/<app>/                      list
GET    /platform/api/files/<app>/<path>                read
PUT    /platform/api/files/<app>/<path>                write
DELETE /platform/api/files/<app>/<path>                delete
```

### JobQueue — async background jobs

```
POST   /platform/api/jobs/<app>/submit/                {"task": "name", "args": {...}}
GET    /platform/api/jobs/<app>/                       list
GET    /platform/api/jobs/<app>/<uuid>/                {"status": "running|done|failed", "progress": 0-100}
POST   /platform/api/jobs/<app>/<uuid>/cancel/
```

### ScitexBridge — call scitex Python from the browser

```
POST   /platform/api/scitex/<module>/<function>/
```

Example: `POST /platform/api/scitex/io/load/` with `{"path": "data.csv"}`.
Modules mirror the `scitex` package: `io`, `plt`, `stats`, etc.

### ExternalAPI — proxy to registered external services

```
GET|POST  /platform/api/external/<api_name>/
```

### Context bootstrap

```
GET  /platform/api/context/
```

Returns project context, user info, and enabled modules. Call at app startup
to hydrate client-side state.

---

## 5. App Editor Template

`templates/shared/app_editor.html` is the generic mount point for apps with
a React or TypeScript frontend.

```html
<div id="app-mount"
     data-app-slug="{{ app_slug }}"
     data-embedded="true"
     data-project-owner="{{ current_project.owner.username }}"
     data-project-slug="{{ current_project.slug }}">
</div>
```

The Vite bundle is loaded via `{% vite_script bridge_entry_name %}`.
App CSS is injected when `app_mount_css` context variable is set.

---

## 6. Scaffold CLI

```bash
scitex-hub app init <dir> --name my_app [--label "My App"] [--frontend react]
```

Generated files:

```
my_app/
├── manifest.json          # Platform registration
├── pyproject.toml         # entry_points["scitex_modules"]
├── apps.py, views.py, urls.py, tests.py, skill.py
├── templates/my_app/
│   ├── index.html         # Full-page view
│   └── index_partial.html # AJAX partial (workspace loads this)
├── static/my_app/css/my_app.css
├── .agents/agents.json
├── AGENTS.md
└── docs/PLATFORM.md       # This reference, auto-generated per-app
# --frontend react also adds: src/index.tsx, App.tsx, store.ts, vite.config.ts
```

---

## 7. Reference Implementation

**figrecipe** at `github.com/ywatanabe1989/figrecipe` — canonical example.

| File | Role |
|---|---|
| `figrecipe/_django/manifest.json` | Platform manifest |
| `figrecipe/_django/views.py` | `build_figrecipe_context(request, current_project)` |
| `figrecipe/_django/templates/figrecipe_app/vis_partial.html` | Workspace partial |
| `figrecipe/_django/__init__.py` | `get_module_config()` entry point |
| `figrecipe/_django/frontend/src/` | React + Vite TypeScript frontend |

---

## Quick Reference

```
Register:        manifest.json + entry_points["scitex_modules"]
Dev install:     POST /apps/store/api/dev/install/  {"owner": "...", "repo": "..."}
Data:            /platform/api/data/<app>/<schema>/
Files:           /platform/api/files/<app>/<path>
Jobs:            /platform/api/jobs/<app>/submit/
scitex calls:    /platform/api/scitex/<module>/<function>/
Bootstrap:       /platform/api/context/
Scaffold:        scitex-hub app init <dir> --name <name> [--frontend react]
Reference:       github.com/ywatanabe1989/figrecipe
```
