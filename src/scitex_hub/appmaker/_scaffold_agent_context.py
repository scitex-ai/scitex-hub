"""Agent context generator for SciTeX app scaffolds.

Generates CLAUDE.md so AI agents can immediately understand
the app structure and build features without manual guidance.
"""

from __future__ import annotations


def _agents_md(name: str, label: str, icon: str, description: str) -> str:
    """Generate AGENTS.md — the agent's full context for building this app."""
    desc = description or "A SciTeX Cloud app."
    return f"""# {label} — SciTeX Cloud App

{desc}

## What This Is

This is a **SciTeX Cloud App** — a plugin that runs as a workspace tab.
Users install it via "Dev Install" from the Hub, and it appears in their sidebar.

## File Structure — What To Edit

```
templates/{name}/index_partial.html   <- YOUR UI (main file to edit)
static/{name}/css/{name}.css          <- YOUR STYLES
views.py                              <- Backend logic / context builder
manifest.json                         <- App metadata (name, icon, description)
```

## How The UI Works

`index_partial.html` is injected into the workspace via AJAX.
It is NOT a full HTML page — no `<html>`, `<head>`, or `<body>` tags.

### Template Rules

1. Start with `{{% load static %}}` for static file references
2. Include your CSS: `<link rel="stylesheet" href="{{% static '{name}/css/{name}.css' %}}">`
3. Wrap everything in a scoped container: `<div class="{name}-container">`
4. Use `data-ai-hint` attributes on key sections for LLM context
5. Keep the template under 1024 lines

### Example Structure

```html
{{% load static %}}
<link rel="stylesheet" href="{{% static '{name}/css/{name}.css' %}}">

<div class="{name}-container" data-pane-type="app">
    <div class="{name}-header" data-ai-hint="App header with title">
        <h2><i class="{icon}"></i> {label}</h2>
    </div>
    <div class="{name}-content" data-ai-hint="Main interactive area">
        <!-- Your app content here -->
    </div>
</div>
```

## CSS Rules

- Scope ALL rules under `.{name}-container` to avoid conflicts
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

`build_{name}_context(request, current_project)` returns template context.
Add any data your template needs here. Keep it simple — no heavy logic.

## Testing

After editing files, the changes are **live immediately** — the workspace
loads templates directly from this directory. Just switch to another tab
and back, or reload the page.

## JavaScript

For interactivity, add `<script>` tags at the bottom of `index_partial.html`.
Keep scripts inline and scoped. For complex apps, create a TypeScript file
in `static/{name}/ts/` and include it via `<script type="module">`.

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
"""


# EOF
