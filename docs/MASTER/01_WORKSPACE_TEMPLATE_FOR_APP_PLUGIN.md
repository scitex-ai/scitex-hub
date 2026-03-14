<!-- ---
!-- Timestamp: 2026-03-01 05:49:14
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/MASTER/01_WORKSPACE_TEMPLATE_FOR_APP_PLUGIN.md
!-- --- -->

# Workspace Template for App Plugins

This document defines what app plugins receive from the workspace frame
and the rules they must follow. The frame is provided by `global_base.html` —
plugins only fill `{% block content %}`.

## What the Frame Provides (not your responsibility)

```
+----------+--------+---------+-----+---------------------------+
| Console  | Files  | Viewer  | App | YOUR CONTENT              |
| Col 1    | Col 2  | Col 3   | Col4| Col 5: {% block content %}|
+----------+--------+---------+-----+---------------------------+
  Auto       Auto     Auto     Auto   You build this
```

The frame handles: sidebar collapse/expand, drag resize, localStorage persistence,
ZenMode (F11/Alt+Z), AJAX tab switching, footer toggle, and theme variables.

## Plugin Rules

### MUST

| # | Rule |
|---|------|
| 1 | Extend `global_base.html` and use `{% block content %}` only |
| 2 | Register module in `apps/workspace_app/registry.py` |
| 3 | Scope all CSS to your module class (e.g., `.myapp-main .card`) |
| 4 | Use `--workspace-*` CSS variables for colors |

### MUST NOT

| # | Rule |
|---|------|
| 1 | Override `{% block workspace_worktree_pane %}` or any other frame block |
| 2 | Hide the footer (`footer { display: none }`) |
| 3 | Style frame elements (`.stx-shell-sidebar`, `.stx-shell-sidebar__title`, `.panel-resizer`) |
| 4 | Use `!important` on any frame element |
| 5 | Create sidebar duplicates (`<aside>` for Files/Viewer/Console) |

## Available APIs

### Template Blocks

| Block | Purpose |
|-------|---------|
| `{% block content %}` | Your module HTML (required) |
| `{% block extra_css %}` | Your CSS `<link>` tags |
| `{% block head_extra %}` | Extra `<head>` elements |

### Context Variables (auto-injected)

| Variable | Type | Example |
|----------|------|---------|
| `active_module_name` | str | `"myapp"` |
| `active_module` | ModuleConfig | `.label`, `.icon`, `.accent_color` |
| `workspace_modules` | list[ModuleConfig] | All user-enabled modules |

### CSS Variables (for theming)

| Variable | Purpose |
|----------|---------|
| `--workspace-bg-primary` | Main background |
| `--workspace-bg-secondary` | Card/panel background |
| `--workspace-bg-tertiary` | Header/inset background |
| `--workspace-border-default` | Borders |
| `--workspace-icon-primary` | Accent color |
| `--text-primary` | Primary text |
| `--text-secondary` | Secondary text |
| `--text-muted` | Muted text |

### JavaScript (auto-available)

| API | What it does |
|-----|-------------|
| `HorizontalResizer` | Auto-inits `[data-h-resizer]` elements (drag resize + collapse) |
| `VerticalResizer` | Auto-inits `[data-v-resizer]` elements (drag resize + collapse) |
| `ZenMode` | F11/Alt+Z sidebar toggle |
| `ModuleTabSwitcher` | AJAX navigation between modules |
| `window.SCITEX_MODULE_COLORS` | Per-module accent colors (from user prefs) |

### REST Endpoints (for workspace operations)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/worktree/` | GET | List project files |
| `/api/worktree/<path>/` | GET | Read file content |
| `/api/worktree/<path>/` | PUT | Write file |
| `/api/worktree/<path>/` | DELETE | Delete file |
| `/api/worktree/upload/` | POST | Upload files |
| `/api/viewer/open/` | POST | Open file in Viewer pane |
| `/api/ai/chat/` | POST | Send message to AI Console |

## Shared UI Components

See **[03_SHARED_UI_COMPONENTS.md](03_SHARED_UI_COMPONENTS.md)** for the full guide. Key components:

| Component | HTML | Purpose |
|-----------|------|---------|
| HorizontalResizer | `<div class="h-resizer" data-h-resizer data-in-app ...>` | Drag-resize + collapse between left/right panels |
| VerticalResizer | `<div class="v-resizer" data-v-resizer data-in-app ...>` | Drag-resize + collapse between top/bottom panels |
| Selector Nav | `<nav class="selector-nav" data-indicator="right">` | Vertical icon+label mode switcher |
| Collapsible Panel | `<div class="collapsible-panel">` | Panels that collapse to icon+label strip |

All styles auto-loaded globally via `common.css`. Plugins only need HTML markup.

## Quickstart: Create a New App

### 1. Register

```python
# apps/workspace_app/registry.py
register_module(ModuleConfig(
    name="myapp",
    label="My App",
    icon="fas fa-cube",
    url_prefix="/myapp/",
    body_class="myapp-page",
    default_enabled=True,
))
```

### 2. Template

```html
{% extends 'global_base.html' %}
{% block content %}
    <div class="myapp-main">
        <!-- Your content here. The five-column frame wraps this automatically. -->
    </div>
{% endblock %}
```

### 3. CSS

```css
/* Scope everything to your module */
.myapp-main { padding: 16px; }
.myapp-main .card {
    background: var(--workspace-bg-secondary);
    border: 1px solid var(--workspace-border-default);
}
```

### 4. Verify

Run the validation checklist from `01_WORKSPACE_TEMPLATE.md` (V1-V4) on your module page.

## Validation Checklist (quick version)

| # | Check | Pass? |
|---|-------|-------|
| 1 | All 5 columns present on your page | |
| 2 | Collapsed panes show icon + text label | |
| 3 | Sidebars expand/collapse normally | |
| 4 | Footer toggle works | |
| 5 | AJAX tab switch to/from your module preserves layout | |
| 6 | Ctrl+Shift+R shows identical layout | |
| 7 | Your CSS does not affect other modules | |

## Examples from Existing Apps

These apps were created before this spec was formalized but follow the pattern.

### Example App (simplest — reference implementation)

```
apps/example_app/templates/example_app/index.html
```

```html
{% extends "global_base.html" %}
{% block content %}
    {% include "example_app/index_partial.html" %}
{% endblock %}
```

Minimal: extends base, fills content block, nothing else. The partial contains
all HTML + a `<link>` tag for its own CSS.

### Hub

```
apps/hub_app/templates/hub_app/index.html
```

```html
{% extends "global_base.html" %}
{% block title %}Hub{% endblock %}
{% block extra_css %}
    <link rel="stylesheet" href="{% static 'hub_app/css/hub.css' %}" />
{% endblock %}
{% block content %}
    {% include "hub_app/index_partial.html" %}
{% endblock %}
```

Compliant: uses `extra_css` for its own styles, content in a partial.

### Writer

```
apps/writer_app/templates/writer_app/writer_base.html
```

```html
{% extends 'global_base.html' %}
{% block extra_css %}...writer-specific CSS...{% endblock %}
{% block content %}
    <main class="writer-main">...</main>
{% endblock %}
```

Compliant: content scoped inside `.writer-main`. Uses `extra_css` for Monaco editor styles.

### Vis

```
apps/figrecipe_app/templates/figrecipe_app/editor.html
```

```html
{% extends "global_base.html" %}
{% block extra_css %}...vis-specific CSS...{% endblock %}
{% block content %}
    <div class="vis-workspace">...</div>
{% endblock %}
```

Compliant: content scoped inside `.vis-workspace`.

### Scholar (was non-compliant, now fixed)

```
apps/scholar_app/templates/scholar_app/scholar_unified.html
```

**Before (broken):**
```html
{% extends 'global_base.html' %}
{% block workspace_worktree_pane %}{% endblock %}  <!-- VIOLATION: removed Files pane -->
{% block content %}
    <div class="scholar-workspace">
        <aside class="scholar-sidebar">...</aside>  <!-- VIOLATION: duplicate sidebar -->
        <main class="scholar-main">...</main>
    </div>
{% endblock %}
```

**After (fixed):**
```html
{% extends 'global_base.html' %}
{% block content %}
    <main class="scholar-main">...</main>  <!-- Only module content -->
{% endblock %}
```

Violations removed: no pane override, no duplicate sidebar.

### Clew

```
apps/clew_app/templates/clew_app/index.html
```

```html
{% extends "global_base.html" %}
{% block extra_css %}...clew CSS...{% endblock %}
{% block content %}
    {% include 'clew_app/index_partial.html' %}
{% endblock %}
```

Compliant: standard pattern with partial.

### Common Pattern (all apps follow this)

```html
{% extends "global_base.html" %}
{% load static vite tree_preseed %}

{% block title %}My Module{% endblock %}
{% block extra_css %}
    <link rel="stylesheet" href="{% static 'myapp/css/styles.css' %}" />
{% endblock %}
{% block content %}
    {% include "myapp/index_partial.html" %}
{% endblock %}
```

Key: full-page template extends base and includes a partial.
The partial is also served standalone for AJAX tab switching via `ModuleTabSwitcher`.

## App Plugin Lifecycle

### Development

| # | Phase | Description |
|---|-------|-------------|
| 1 | **Scaffold** | Clone `~/proj/scitex-app-template` — includes boilerplate, validation panel, self-descriptive rendering tools (Django views + real API endpoints) |
| 2 | **Implement** | Build your module inside `{% block content %}`. Use workspace APIs for files, viewer, and AI integration |
| 3 | **Validate** | Run `python manage.py validate_workspace_frame` to check frame compliance |
| 4 | **Test** | Write tests using `ModuleTestMixin` — validates registration, hints, CSS scoping, and skill integration |
| 5 | **Version** | Follow semver (vX.Y.Z). Update `pyproject.toml` and tag |

### Submission

| # | Phase | Description |
|---|-------|-------------|
| 6 | **Manifest** | Provide `manifest.json` with module metadata: name, version, author, ORCID, description, icon, dependencies |
| 7 | **CI Check** | Automated pipeline runs frame validator, CSS scope check, file size limits, and test suite |
| 8 | **Submit** | Push to app registry via `scitex app submit` |
| 9 | **Auto Validation** | Server-side checks: template compliance, no frame overrides, CSS isolation, security scan |
| 10 | **Human Review** | Maintainer review for UX quality, code standards, and documentation |

### Safety Measures

| # | Measure | Description |
|---|---------|-------------|
| 11 | **ORCID-linked authors** | During preview phase, only ORCID-verified users can publish plugins |
| 12 | **Issue reporting** | Users can report bugs or policy violations directly from the app page |
| 13 | **Review & ratings** | Community ratings inform trust level and visibility in the app browser |

### Reusable Template

The canonical starting point for new plugins:

```
~/proj/scitex-app-template/
├── apps/your_app/
│   ├── __init__.py
│   ├── apps.py               # AppConfig
│   ├── views.py               # index_view + build_context
│   ├── urls.py                # URL patterns
│   ├── skill.py               # LLM skill registration
│   ├── tests.py               # ModuleTestMixin
│   ├── templates/your_app/
│   │   ├── index.html         # Extends global_base.html
│   │   └── index_partial.html # Standalone AJAX partial
│   └── static/your_app/css/
│       └── your.css           # Scoped module styles
├── manifest.json              # Plugin metadata
└── pyproject.toml             # Packaging
```

### Automated Validator

```bash
# Static checks (template + CSS compliance)
python manage.py validate_workspace_frame

# Static + live HTTP checks (requires running server)
python manage.py validate_workspace_frame --live

# Custom server URL
python manage.py validate_workspace_frame --live --base-url http://localhost:8080
```

Checks performed:
- Template extends `global_base.html` (walks `{% extends %}` chain)
- No `{% block workspace_worktree_pane %}` override
- Has `{% block content %}`
- CSS does not override `.stx-shell-sidebar__title` font-size
- CSS does not hide footer with `display: none`
- CSS does not use `!important` on protected frame selectors
- (Live) All 6 frame element IDs present in rendered HTML
- (Live) No `font-size: 0` on `.stx-shell-sidebar__title` inline styles


### Necessary Assets
- [x] Icon — Font Awesome class (e.g. `fas fa-puzzle-piece`), set in `/new/?type=app` form and `manifest.json`
- [x] Subtitle — short tagline, stored in `manifest.json`
- [x] License — AGPL-3.0 by default, supports MIT, Apache-2.0, BSD-3-Clause, GPL-3.0, LGPL-3.0, MPL-2.0, Proprietary
- [x] About — 1-line description, doubles as `ai_hint` for LLM context
- [x] Capabilities / Skills — comma-separated, for agents and humans
- [x] Supported filetypes — optional file extension filter for workspace file tree (`allowed_extensions` in registry)
- [x] WIP state — checkbox in create form, `status: "wip"` in registry
- [x] `data-ai-hint` tags on important HTML elements — for agent navigation and QA
- [ ] Optional MCP server

#### manifest.json Spec

All app plugins provide a `manifest.json` at project root:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Module display name |
| `slug` | Yes | — | URL slug (lowercase, hyphens) |
| `icon` | Yes | `fas fa-puzzle-piece` | Font Awesome class for tab bar |
| `subtitle` | Yes | — | Short tagline (max 80 chars) |
| `about` | Yes | — | One-line description (max 200 chars) |
| `license` | Yes | `AGPL-3.0` | SPDX identifier |
| `capabilities` | Yes | `[]` | Skills list for agents and humans |
| `supported_filetypes` | No | `[]` | File extensions for tree filter |
| `wip` | No | `true` | WIP badge in Apps browser |
| `version` | Yes | `0.1.0` | Semver string |
| `author` | Yes | — | Username or ORCID |
| `mcp_server` | No | — | Optional MCP server config |

#### `data-ai-hint` Convention

Significant HTML elements MUST include `data-ai-hint="..."` for AI agent navigation:
- Add to: workspace containers, form groups, interactive elements
- Keep concise (1 sentence), active voice
- Existing pattern: `console_app/workspace.html`, `writer_app/index.html`
- Registry `ModuleConfig.ai_hint` provides the top-level module hint

### Available Resources for App Plugins

| Resource | Description |
|----------|-------------|
| **LLM** | Chat + tool use via litellm-supported models (OpenAI, Anthropic, etc.) |
| **Terminal** | Claude Code, Gemini CLI, Codex — available in workspace console |
| **Files** | Project files via workspace file tree + REST API (`/api/worktree/`) |

### App Ecosystem Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | App detail page (e.g. `/apps/writer/`) auto-populated from `manifest.json` + registry | Planned |
| 2 | User-driven install/uninstall without admin interaction (via `ModuleInstallation`) | Available |
| 3 | Permission model: Private / Public / Group / Collaborator (GitHub-style) | Available |
| 4 | OSS development via Issues and Pull Requests encouraged | Available |
| 5 | Citable template for research papers referencing app plugins | Planned |
| 6 | Proprietary apps accepted; no payment infrastructure provided | Policy |
| 7 | Licensing details documented in Docs app (`/docs/?section=licensing`) | Available |

<!-- EOF -->
