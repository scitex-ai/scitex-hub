"""HTML template generators for the SciTeX app scaffold."""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Django / Python file generators
# ---------------------------------------------------------------------------


def _apps_py(name, label, class_name):
    return f'''"""Django app configuration for {label}."""

from django.apps import AppConfig


class {class_name}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{name}"
    verbose_name = "{label}"
'''


def _views_py(name, label, description):
    desc = description or f"A SciTeX Cloud app for {label}."
    return f'''"""Views for {label} workspace app."""

from __future__ import annotations

from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project


def build_{name}_context(request, current_project=None):
    """Context builder called by workspace registry for AJAX partial loads."""
    return {{
        "current_project": current_project,
        "app_name": "{label}",
        "app_description": "{desc}",
        "features": [
            "Workspace app integration",
            "AJAX partial loading",
            "Scoped CSS with theme variables",
        ],
    }}


def index_view(request):
    """Full page view for {label}."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = build_{name}_context(request, current_project=current_project)
    return render(request, "{name}/index.html", context)


# EOF
'''


def _urls_py(name):
    return f'''"""URL configuration for {name}."""

from django.urls import path

from . import views

app_name = "{name}"

urlpatterns = [
    path("", views.index_view, name="index"),
]
'''


def _tests_py(name, label):
    module_name = name.removesuffix("_app")
    class_label = label.replace(" ", "")
    return f'''"""Tests for {label} workspace app."""

from django.test import TestCase

from apps.workspace_app.test_mixin import ModuleTestMixin


class {class_label}ModuleTest(ModuleTestMixin, TestCase):
    """Registry integration tests for {label} (auto-validated by ModuleTestMixin)."""

    module_name = "{module_name}"


class {class_label}ContextTest(TestCase):
    """Unit tests for {label} context builder."""

    def test_context_has_required_keys(self):
        """Context builder returns all expected keys."""
        from django.test import RequestFactory
        from django.contrib.auth.models import User

        from apps.{name}.views import build_{name}_context

        factory = RequestFactory()
        request = factory.get("/{name}/")
        request.user = User(username="testuser")

        ctx = build_{name}_context(request)
        self.assertIn("app_name", ctx)
        self.assertEqual(ctx["app_name"], "{label}")
        self.assertIn("app_description", ctx)
        self.assertIn("features", ctx)
        self.assertIsInstance(ctx["features"], list)


# EOF
'''


def _skill_py(name, label, description):
    desc = description or f"A SciTeX Cloud app for {label}."
    caps = _derive_capabilities(label, description)
    caps_str = json.dumps(caps, ensure_ascii=False)
    return f'''"""Skill registration for {label}."""

from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="{name}",
        display_name="{label}",
        description="{desc}",
        capabilities={caps_str},
        page_patterns=["/{name}/"],
        url_prefix="/{name}/",
        app_description="{desc}",
    )
)
'''


def _derive_capabilities(label, description):
    """Derive 2-3 capabilities from description or use sensible defaults."""
    if not description:
        return [
            f"View {label} content",
            f"Interact with {label} workspace",
        ]
    words = description.lower()
    caps = [f"View {label} content"]
    if any(w in words for w in ("visual", "display", "plot", "chart", "graph")):
        caps.append(f"Visualize {label.lower()} data")
    if any(w in words for w in ("analy", "process", "comput", "calculat")):
        caps.append(f"Analyze {label.lower()} data")
    if any(w in words for w in ("edit", "creat", "write", "manag")):
        caps.append(f"Manage {label.lower()} resources")
    if len(caps) < 2:
        caps.append(f"Interact with {label} workspace")
    return caps[:3]


def _manifest_json(name, label, icon, description, extra_manifest, license_id):
    slug = name.replace("_", "-")
    desc = description or "A SciTeX Cloud app."
    manifest = {
        "name": name,
        "slug": slug,
        "label": label,
        "version": "0.1.0",
        "icon": icon,
        "subtitle": desc[:80],
        "about": desc[:200],
        "description": desc,
        "author": "",
        "license": license_id,
        "capabilities": [],
        "allowed_extensions": [],
        "wip": True,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# HTML template generators
# ---------------------------------------------------------------------------


def _index_html(name, label, *, include_js_bundle: bool = False):
    bundle_tag = ""
    if include_js_bundle:
        bundle_tag = f'\n    <script type="module" src="{{% static \'{name}/js/main.js\' %}}"></script>'
    return f"""{{% extends "global_base.html" %}}
{{% load static %}}
{{% block extra_css %}}
    <link rel="stylesheet" href="{{% static '{name}/css/{name}.css' %}}">
{{% endblock %}}
{{% block extra_js %}}{bundle_tag}
{{% endblock %}}
{{% block content %}}
    {{% include "{name}/index_partial.html" %}}
{{% endblock %}}
"""


def _index_partial_html(name, label, icon, *, react_mount: bool = False):
    mount_div = ""
    if react_mount:
        mount_div = f'\n    <div id="{name}-root"></div>\n'
    return f"""{{% load static %}}
<div class="{name}-container" data-pane-type="app"
     data-ai-hint="Main container for {label} app">
    <div class="{name}-header" data-ai-hint="{label} app header">
        <h2><i class="{icon}"></i> {label}</h2>
        <p class="{name}-subtitle">Welcome to {label}. Edit this template to build your app.</p>
    </div>

    <div class="{name}-content" data-ai-hint="{label} content area">
        <div class="{name}-getting-started">
            <h3>Getting Started</h3>
            <ol class="{name}-steps">
                <li>
                    <strong>Build your UI</strong> &mdash;
                    Edit <code>templates/{name}/index_partial.html</code>
                </li>
                <li>
                    <strong>Add logic</strong> &mdash;
                    Update the context builder in <code>views.py</code>
                </li>
                <li>
                    <strong>Style it</strong> &mdash;
                    Customize <code>static/{name}/css/{name}.css</code>
                </li>
            </ol>
        </div>
{mount_div}
        <div class="{name}-placeholder">
            <i class="{icon}" style="font-size: 3rem; opacity: 0.3;"></i>
            <p>Your app content goes here.</p>
        </div>
    </div>
</div>
"""


def _app_css(name, label):
    return f"""/* Styles for {label} workspace app */

.{name}-container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
}}

.{name}-header {{
    margin-bottom: 1.5rem;
}}

.{name}-header h2 {{
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.5rem;
}}

.{name}-subtitle {{
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
}}

.{name}-content {{
    background: var(--workspace-bg-secondary);
    border: 1px solid var(--workspace-border-default);
    border-radius: 6px;
    padding: 2rem;
}}

.{name}-getting-started {{
    margin-bottom: 2rem;
}}

.{name}-getting-started h3 {{
    font-size: 1.125rem;
    color: var(--text-primary);
    margin: 0 0 1rem;
}}

.{name}-steps {{
    padding-left: 1.25rem;
    color: var(--text-secondary);
    line-height: 1.8;
}}

.{name}-steps code {{
    background: var(--workspace-bg-tertiary);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8125rem;
}}

.{name}-card {{
    background: var(--workspace-bg-tertiary);
    border: 1px solid var(--workspace-border-default);
    border-radius: 6px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}}

.{name}-placeholder {{
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-muted);
}}

.{name}-placeholder p {{
    margin: 0.5rem 0;
}}

@media (max-width: 768px) {{
    .{name}-container {{
        padding: 1rem;
    }}

    .{name}-content {{
        padding: 1rem;
    }}
}}
"""


def _agents_json(name, label):
    config = {
        "version": 3,
        "agents": {
            "default": {
                "name": f"{name}-agent",
                "model": "claude-sonnet-4-6",
                "instructions": f"You are a helpful assistant for the {label} app.",
            }
        },
    }
    return json.dumps(config, indent=2) + "\n"


def _readme_md(name, label, description, license_id, *, frontend_type: str = "html"):
    desc = description or "A SciTeX Cloud App plugin."
    frontend_section = ""
    if frontend_type == "react":
        frontend_section = f"""
## Frontend (React)

The `frontend/` directory contains a React+Vite+Zustand setup.

```
frontend/
  package.json         # npm dependencies
  vite.config.ts       # Vite config (outputs to static/{name}/js/)
  tsconfig.json        # TypeScript config
  src/
    main.tsx           # Entry point — mounts <App /> to #{name}-root
    App.tsx            # Root component
    store/
      useAppStore.ts   # Zustand state store
```

### Development

```bash
cd frontend
npm install
npm run dev    # watch mode
npm run build  # production build
```
"""
    return f"""# {label}

{desc}

## Structure

```
{name}/
  __init__.py          # App init
  apps.py              # Django AppConfig
  views.py             # View functions and context builder
  urls.py              # URL routing
  tests.py             # Test suite
  skill.py             # LLM skill registration
  manifest.json        # App metadata
  templates/{name}/    # HTML templates
    index.html         # Full page (extends global_base)
    index_partial.html # AJAX-loadable partial
  static/{name}/css/   # Scoped stylesheets
  .agents/             # AI agent configuration
  LICENSE              # License file
  README.md            # This file
```
{frontend_section}
## Development

1. Edit `templates/{name}/index_partial.html` to build your UI
2. Add view logic in `views.py`
3. Add styles in `static/{name}/css/{name}.css`
4. Run tests: `pytest apps/{name}/tests.py`

## Testing in Workspace

To test your app in the SciTeX workspace:

1. Register in `apps/workspace_app/registry.py` as an external module
2. Restart Django: `make env=dev restart`
3. Your app appears in the workspace sidebar

## Submission

When ready to publish:

1. Run validation: `scitex-cloud app validate .`
2. Submit: use the Apps settings panel in your project

## License

{label} is licensed under {license_id} — see `LICENSE` for details.
"""


# EOF
