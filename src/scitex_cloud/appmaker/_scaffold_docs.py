"""Platform documentation generator for SciTeX app scaffolds.

Generates docs/PLATFORM.md — comprehensive platform reference for AI agents
working on app projects. Content extracted from the App Maker documentation.
"""

from __future__ import annotations


def _platform_docs_md(name: str) -> str:
    """Generate docs/PLATFORM.md — full platform reference for agents."""
    module_name = name.removesuffix("_app")
    return f"""# SciTeX Cloud App Platform Reference

This document is the comprehensive platform reference for building SciTeX Cloud
apps. For a quick-start guide, see `AGENTS.md` in the project root.

---

## Architecture

Every workspace module consists of 6 layers:

| Layer | File | Purpose |
|-------|------|---------|
| 1. Registry | `workspace_app/registry.py` | ModuleConfig entry — single source of truth |
| 2. Views | `your_app/views.py` | Full page view + context builder function |
| 3. Templates | `your_app/templates/` | `index.html` (full page) + `index_partial.html` (AJAX) |
| 4. URLs | `config/urls.py` | URL pattern registration |
| 5. Skill | `your_app/skill.py` | LLM integration — capabilities, tool prefixes |
| 6. Tests | `your_app/tests.py` | ModuleTestMixin validates all layers automatically |

---

## Platform Services

Apps can use 7 built-in Platform Services via REST APIs instead of writing
custom Django models, views, or Celery tasks. Build powerful apps with just
a `manifest.yaml` and frontend code.

| Service | API Prefix | Purpose |
|---------|-----------|---------|
| **DataStore** | `/platform/api/data/` | JSON-based CRUD with indexed virtual columns |
| **FileVault** | `/platform/api/files/` | File upload/download scoped to app + project |
| **JobQueue** | `/platform/api/jobs/` | Background task execution via Celery |
| **ScitexBridge** | `/platform/api/scitex/` | Proxy to `scitex` Python package (io, stats, plt) |
| **ExternalAPI** | `/platform/api/external/` | Proxied HTTP calls to whitelisted external services |
| **RealtimeHub** | `ws://` | WebSocket channels for live updates |
| **FrontendKit** | — | Shared TS components (DataTable, Monaco, Viewer) |

### DataStore Example

No Django models required. Define schemas in `manifest.yaml`:

```yaml
datastore:
  Sample:
    fields:
      name: {{type: string, max_length: 200, indexed: true}}
      condition: {{type: string, max_length: 100, indexed: true}}
      measurement: {{type: float}}
      notes: {{type: text}}
      recorded_at: {{type: datetime}}
      tags: {{type: json}}
    permissions: owner_and_collaborators
```

Frontend calls `/platform/api/data/your-app/Sample/` for CRUD operations.
Virtual indexed columns are created automatically — no Django migrations needed.

---

## Python SDK (`scitex_cloud.sdk`)

Instead of constructing raw HTTP requests, use the Python SDK from your
context builder or any backend code running inside Apptainer:

```python
from scitex_cloud.sdk import data, files, jobs

# DataStore — CRUD
data.create("{name}", "Sample", {{"name": "Test", "condition": "A"}})
data.list_records("{name}", "Sample", filters={{"condition": "A"}})
data.get("{name}", "Sample", record_id)
data.update("{name}", "Sample", record_id, {{"condition": "B"}})
data.delete("{name}", "Sample", record_id)
data.search("{name}", "Sample", query="neural")

# FileVault — file storage
files.upload("{name}", "exports/data.csv", csv_content)
files.download("{name}", "exports/data.csv")
files.list_files("{name}", path="exports/")
files.delete("{name}", "exports/data.csv")

# JobQueue — background tasks
jobs.submit("{name}", "export_csv", params={{"format": "xlsx"}})
jobs.status("{name}", job_id)
jobs.list_jobs("{name}")
```

Auth is automatic via `SCITEX_API_TOKEN` env var (injected into Apptainer).

**CLI equivalent:**
```bash
scitex-cloud sdk data list {name} Sample
scitex-cloud sdk files upload {name} local.csv exports/data.csv
scitex-cloud sdk jobs submit {name} export_csv --params '{{"format":"xlsx"}}'
```

---

## Unified Context (`GET /platform/api/context/`)

Bootstrap your app with one call — returns user profile, project metadata,
and file tree:

```python
from scitex_cloud.sdk._client import get_client
result = get_client().request("GET", "/platform/api/context/", params={{"project_id": pid}})
# result["context"]["user"]     -> {{"id": ..., "username": ..., "email": ...}}
# result["context"]["project"]  -> {{"id": ..., "name": ..., "slug": ...}}
# result["context"]["file_tree"] -> [{{"path": "...", "is_dir": true/false}}, ...]
```

---

## Manifest

A `manifest.yaml` declares your app's data schemas, jobs, and service
dependencies. Platform Services read this file to auto-configure everything.

```yaml
name: {name}
label: Your App Label
version: 0.1.0
icon: fas fa-puzzle-piece
category: data
description: Short description of your app.

datastore:
  ModelName:
    fields:
      field_name: {{type: string, max_length: 200, indexed: true}}
    permissions: owner_and_collaborators

jobs:
  job_name:
    handler: {name}.jobs.job_name.execute

scitex_modules: [io, stats]
```

---

## ModuleConfig Fields

Every module is defined by a `ModuleConfig` dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | URL slug (e.g., `"writer"`) |
| `label` | str | Display name (e.g., `"Writer"`) |
| `app_name` | str | Django app name (e.g., `"writer_app"`) |
| `icon_fa` | str | FontAwesome class (e.g., `"fas fa-pen"`) |
| `partial_template` | str | AJAX partial template path |
| `context_builder` | str | Dotted path to context function |
| `keyboard_shortcut` | str | Alt+key shortcut (single letter) |
| `order` | int | Tab bar position (lower = leftmost) |
| `status` | str | `"stable"`, `"wip"`, `"beta"`, `"deprecated"` |
| `default_enabled` | bool | Show in tab bar for new users |
| `ai_hint` | str | Short description for LLM context |
| `accent_color` | str | CSS variable name for module accent |

---

## Template System

### Two Templates Required

1. **`index.html`** — Full page (direct URL access):
```html
{{% extends "global_base.html" %}}
{{% block content %}}
    {{% include "{name}/index_partial.html" %}}
{{% endblock %}}
```

2. **`index_partial.html`** — AJAX partial (tab switching):
```html
<div class="{name}-container" data-pane-type="app">
    <!-- Your module content here -->
</div>
```

### Template Rules

- Partials are standalone HTML fragments, NOT full pages
- No `<html>`, `<head>`, or `<body>` tags in partials
- Start with `{{% load static %}}` for static file references
- Root element must have `data-pane-type="app"`
- Use `data-ai-hint` attributes on key sections for LLM context
- Max 1024 lines per template file
- No `{{% extends %}}` in partials

---

## Context Builder

The context builder function provides data to your template. It is called on
both full page loads and AJAX partial loads.

```python
def build_{name}_context(request, current_project=None):
    \"\"\"Called by workspace shell for SPA tab switching.\"\"\"
    return {{
        "current_project": current_project,
        "my_data": [],  # Your data here
    }}

def index_view(request):
    \"\"\"Full page view.\"\"\"
    from apps.infra.project_app.services.project_utils import get_current_project
    project = get_current_project(request)
    context = build_{name}_context(request, project)
    return render(request, "{name}/index.html", context)
```

---

## LLM Skill Registration

Register a Skill so AI assistants understand your module's capabilities:

```python
from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="{name}",
        display_name="Your App - Description",
        description="Detailed description for LLM context...",
        capabilities=[
            "Do something useful",
            "Process data",
        ],
        page_patterns=["/{name}/"],
        url_prefix="/{name}/",
        module_description="One-line summary.",
    )
)
```

---

## CSS Variables & Theming

Scope ALL CSS under `.{name}-container` to prevent style leaks.
Use workspace CSS variables — no hardcoded colors.

```css
.{name}-container {{
    --app-accent: var(--color-accent-emphasis, #4a90d9);
}}
.{name}-container .my-card {{
    background: var(--workspace-bg-secondary);
    border: 1px solid var(--workspace-border-default);
    color: var(--workspace-text-primary);
}}
```

### Available Theme Variables

| Variable | Description |
|----------|-------------|
| `--workspace-bg-primary` | Main background color |
| `--workspace-bg-secondary` | Secondary/card background |
| `--workspace-bg-tertiary` | Nested element background |
| `--workspace-text-primary` | Main text color |
| `--workspace-text-secondary` | Subdued text color |
| `--workspace-border-default` | Subtle border color |
| `--color-accent-emphasis` | Global accent color |

---

## Shared UI Components

Apps can use pre-built UI components (all auto-loaded):

| Category | Contents |
|----------|----------|
| **Components** | Resizer, DataTable, MediaViewer, Selector Nav, File Tabs |
| **Utilities** | API Client, CSRF, StorageManager, Toast/Modal, Theme, Keyboard Shortcuts |
| **CSS System** | Design tokens, theme system, layout utilities, component styles |

---

## Testing

`ModuleTestMixin` automatically validates all module layers:

```python
from django.test import TestCase
from apps.infra.workspace_app.test_mixin import ModuleTestMixin

class MyModuleTest(ModuleTestMixin, TestCase):
    module_name = "{module_name}"
```

This validates:

| Check | What it verifies |
|-------|-----------------|
| `test_module_registered` | Module exists in registry |
| `test_partial_template_exists` | AJAX partial template file exists |
| `test_icon_registered` | Has FontAwesome or SVG icon |
| `test_context_builder_importable` | Context builder function is callable |
| `test_ai_hint_defined` | LLM hint text is non-empty |
| `test_accent_color_css_exists` | CSS variable defined |
| `test_skill_registered` | Skill exists in LLM registry |

---

## Submission Workflow

Apps follow a two-tier distribution model:

1. **Scaffold:** `scitex-cloud app init .` — creates all boilerplate
2. **Develop:** Edit templates, views, and CSS in your project
3. **Validate:** `scitex-cloud app validate .` — checks structure and security
4. **Submit:** `scitex-cloud app submit .` — opens a PR on `scitex/apps` registry
5. **Review:** Staff reviews the PR and merges to approve
6. **Live:** Merged apps appear in the public Apps catalog

### Dev Install (No Approval Needed)

Any user can dev-install your app directly from Hub Explore without going
through the submission process. Dev installs are personal and only visible
to the user who installed them.

### Security Scanning

Source code is automatically scanned for forbidden patterns (`os.system`,
`subprocess`, `eval`, `exec`) before submission. The commit SHA is pinned
on approval for reproducibility.

---

## Licensing

SciTeX uses a layered licensing model:

| Component | License | Copyleft? |
|-----------|---------|-----------|
| SciTeX Cloud Platform | AGPL-3.0 | Yes (strong) |
| App Maker SDK / API | Apache-2.0 | No |
| User Apps | Author's choice | Depends on chosen license |

Apps using the SciTeX workspace API are **not** derivative works of the
AGPL-licensed core. You are free to license your app however you wish.

---

## File Size Limits

- Python/TypeScript/CSS: max 512 lines per file
- HTML templates: max 1024 lines per file
- No inline styles — use CSS classes
- No hardcoded colors — use CSS variables
- No silent fallbacks — show errors explicitly

---

## Per-Package Deep Dives

Each SciTeX package maintains its own `APP_DEVELOPER_GUIDE.md`:

| Package | Install | Guide Covers |
|---------|---------|-------------|
| **scitex-ui** | `pip install scitex-ui` | React components, bridge contract, CSS theme, usePanelResize |
| **scitex-app** | `pip install scitex-app` | FilesBackend SDK, ScitexAppConfig, manifest schema, validation |

Reference implementation: **figrecipe** (github.com/ywatanabe1989/figrecipe)
"""


# EOF
