# Agentic Journal — SciTeX Cloud App

ARA-native open publishing with AI review

## What This Is

This is a **SciTeX Cloud App** — a plugin that runs as a workspace tab.
Users install it via "Dev Install" from the Hub, and it appears in their sidebar.

## File Structure — What To Edit

```
templates/scitex_agentic_journal_hub_app/index_partial.html   <- YOUR UI (main file to edit)
static/scitex_agentic_journal_hub_app/css/scitex_agentic_journal_hub_app.css          <- YOUR STYLES
views.py                              <- Backend logic / context builder
manifest.json                         <- App metadata (name, icon, description)
```

## How The UI Works

`index_partial.html` is injected into the workspace via AJAX.
It is NOT a full HTML page — no `<html>`, `<head>`, or `<body>` tags.

### Template Rules

1. Start with `{% load static %}` for static file references
2. Include your CSS: `<link rel="stylesheet" href="{% static 'scitex_agentic_journal_hub_app/css/scitex_agentic_journal_hub_app.css' %}">`
3. Wrap everything in a scoped container: `<div class="scitex_agentic_journal_hub_app-container">`
4. Use `data-ai-hint` attributes on key sections for LLM context
5. Keep the template under 1024 lines

### Example Structure

```html
{% load static %}
<link rel="stylesheet" href="{% static 'scitex_agentic_journal_hub_app/css/scitex_agentic_journal_hub_app.css' %}">

<div class="scitex_agentic_journal_hub_app-container" data-pane-type="app">
    <div class="scitex_agentic_journal_hub_app-header" data-ai-hint="App header with title">
        <h2><i class="fas fa-book"></i> Agentic Journal</h2>
    </div>
    <div class="scitex_agentic_journal_hub_app-content" data-ai-hint="Main interactive area">
        <!-- Your app content here -->
    </div>
</div>
```

## CSS Rules

- Scope ALL rules under `.scitex_agentic_journal_hub_app-container` to avoid conflicts
- ONLY use `--workspace-*` CSS variables — no hardcoded colors
- Available variables:
  - `--workspace-bg-primary` — main background
  - `--workspace-bg-secondary` — card/panel background
  - `--workspace-bg-tertiary` — nested element background
  - `--workspace-border-default` — borders
  - `--workspace-text-primary` — main text
  - `--workspace-text-secondary` — secondary/muted text (use for subtitles, placeholders, captions)
  - `--color-accent-emphasis` — accent/highlight color
- Keep CSS under 512 lines

## Backend (views.py)

`build_scitex_agentic_journal_hub_app_context(request, current_project)` returns template context.
Add any data your template needs here. Keep it simple — no heavy logic.

## Testing

After editing files, the changes are **live immediately** — the workspace
loads templates directly from this directory. Just switch to another tab
and back, or reload the page.

## JavaScript / React

For interactivity, add `<script>` tags at the bottom of `index_partial.html`.
Keep scripts inline and scoped. For complex apps, create a TypeScript file
in `static/{name}/ts/` and include it via `<script type="module">`.


## Standalone Mode

This app can run in two modes:

1. **Standalone** (`my-app gui`): Full workspace shell runs locally
   - Console/terminal, file tree, viewer, and your app — all in one window
   - Uses `scitex_app._standalone.run_standalone()` for the Django server
   - Theme CSS and workspace layout from scitex-ui
   - No cloud server needed

2. **Embedded** (inside SciTeX Cloud): App appears as a workspace tab
   - Installed via Dev Install from the Hub
   - Same code, same UI — just mounted inside the cloud workspace

Both modes use the same React components from scitex-ui.

## Key Constraints

- Files: PY/TS/CSS max 512 lines, HTML max 1024 lines
- No inline styles — use CSS classes
- No hardcoded colors — use CSS variables
- No silent fallbacks — show errors explicitly
- This app runs inside the SciTeX workspace (dark theme)

## Deep Reference — Per-Package Guides

Each SciTeX package owns its own AI agent documentation. Read these for full API details:

| Package | Guide | What It Covers |
|---------|-------|----------------|
| **scitex-ui** | `pip show scitex-ui` → docs/APP_DEVELOPER_GUIDE.md | React components (DataTable, FileBrowser), bridge contract, theme CSS, usePanelResize |
| **scitex-app** | `pip show scitex-app` → docs/APP_DEVELOPER_GUIDE.md | FilesBackend SDK, ScitexAppConfig, manifest schema, AppValidator |
| **scitex-cloud** | Platform docs/APP_DEVELOPER_GUIDE.md | Platform services (DataStore, FileVault, JobQueue), dev install, workspace integration |

### Reference Implementation

**FigRecipe** (github.com/ywatanabe1989/figrecipe) is a complete working app.

Key files to study:
- `src/figrecipe/_django/manifest.json` — app manifest
- `src/figrecipe/_django/views.py` — Django views (editor_page + api_dispatch)
- `src/figrecipe/_django/handlers/` — thin API handlers delegating to Python core
- `src/figrecipe/_django/frontend/src/bridge/bridge-init.ts` — bridge entry point
- `src/figrecipe/_django/frontend/src/InnerEditor.tsx` — React editor layout

### Platform Docs

For platform services, workspace APIs, and submission workflow:

Read `docs/PLATFORM.md`
