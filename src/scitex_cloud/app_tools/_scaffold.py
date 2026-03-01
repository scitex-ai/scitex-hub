"""App scaffold — generate complete boilerplate for a SciTeX app plugin."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ._license import generate_license_text

logger = logging.getLogger(__name__)


def scaffold(
    target_dir: str | Path,
    name: str,
    *,
    label: str = "",
    icon: str = "fas fa-puzzle-piece",
    description: str = "",
    manifest: Optional[dict] = None,
    license_id: str = "AGPL-3.0",
    overwrite: bool = False,
) -> list[str]:
    """Generate complete app boilerplate in target_dir.

    Parameters
    ----------
    target_dir : path
        Project directory (e.g. data/users/alice/proj/my_app/).
    name : str
        Python module name (must end with _app, e.g. 'my_awesome_app').
    label : str
        Human-readable label (default: derived from name).
    icon : str
        Font Awesome icon class (default: 'fas fa-puzzle-piece').
    description : str
        Short description for the app.
    manifest : dict, optional
        Extra manifest fields to merge.
    license_id : str
        SPDX license identifier (default: 'AGPL-3.0').
    overwrite : bool
        If True, overwrite existing files (default: False).

    Returns
    -------
    list[str]
        Relative paths of created files.
    """
    target = Path(target_dir)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    if not label:
        label = name.replace("_", " ").title().removesuffix(" App")

    class_name = label.replace(" ", "") + "App"
    files = _build_all_files(
        name, label, class_name, icon, description, manifest, license_id
    )

    created = []
    for relpath, content in files.items():
        filepath = target / relpath
        if filepath.exists() and not overwrite:
            logger.debug("Skipping existing file: %s", relpath)
            continue
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        created.append(relpath)
        logger.debug("Created: %s", relpath)

    logger.info("Scaffolded %d/%d files in %s", len(created), len(files), target)
    return created


def _build_all_files(name, label, class_name, icon, description, manifest, license_id):
    """Build dict of relpath -> content for all scaffold files."""
    files = {}

    # __init__.py
    files["__init__.py"] = f'"""SciTeX App: {label}."""\n'

    # apps.py
    files["apps.py"] = _apps_py(name, label, class_name)

    # views.py
    files["views.py"] = _views_py(name, label, description)

    # urls.py
    files["urls.py"] = _urls_py(name)

    # tests.py
    files["tests.py"] = _tests_py(name, label)

    # skill.py
    files["skill.py"] = _skill_py(name, label, description)

    # manifest.json
    files["manifest.json"] = _manifest_json(
        name, label, icon, description, manifest, license_id
    )

    # Templates
    files[f"templates/{name}/index.html"] = _index_html(name, label)
    files[f"templates/{name}/index_partial.html"] = _index_partial_html(
        name, label, icon
    )

    # Static CSS
    files[f"static/{name}/css/{name}.css"] = _app_css(name, label)

    # Agents config
    files[".agents/agents.json"] = _agents_json(name, label)

    # README
    files["README.md"] = _readme_md(name, label, description, license_id)

    # LICENSE
    license_text = generate_license_text(license_id)
    if license_text is None:
        license_text = generate_license_text("AGPL-3.0")
    files["LICENSE"] = license_text

    return files


# ---------------------------------------------------------------------------
# Template generators
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
    desc = description or f"A SciTeX app module for {label}."
    return f'''"""Views for {label} workspace module."""

from __future__ import annotations

from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project


def build_{name}_context(request, current_project=None):
    """Context builder called by workspace registry for AJAX partial loads."""
    return {{
        "current_project": current_project,
        "module_name": "{label}",
        "module_description": "{desc}",
        "features": [
            "Workspace module integration",
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
    return f'''"""Tests for {label} workspace module."""

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
        self.assertIn("module_name", ctx)
        self.assertEqual(ctx["module_name"], "{label}")
        self.assertIn("module_description", ctx)
        self.assertIn("features", ctx)
        self.assertIsInstance(ctx["features"], list)


# EOF
'''


def _skill_py(name, label, description):
    desc = description or f"A SciTeX app module for {label}."
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
        module_description="{desc}",
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
    manifest = {
        "name": name,
        "label": label,
        "version": "0.1.0",
        "icon": icon,
        "description": description or "A SciTeX app module.",
        "license": license_id,
        "capabilities": [],
        "allowed_extensions": [],
        "wip": False,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _index_html(name, label):
    return f"""{{% extends "global_base.html" %}}
{{% load static %}}
{{% block content %}}
    <link rel="stylesheet" href="{{% static '{name}/css/{name}.css' %}}">
    {{% include "{name}/index_partial.html" %}}
{{% endblock %}}
"""


def _index_partial_html(name, label, icon):
    return f"""<div class="{name}-container" data-module-accent data-pane-type="module">
    <div class="{name}-header">
        <h2><i class="{icon}"></i> {label}</h2>
        <p class="{name}-subtitle">Welcome to {label}. Edit this template to build your app.</p>
    </div>

    <div class="{name}-content">
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

        <div class="{name}-placeholder">
            <i class="{icon}" style="font-size: 3rem; opacity: 0.3;"></i>
            <p>Your app content goes here.</p>
        </div>
    </div>
</div>
"""


def _app_css(name, label):
    return f"""/* Styles for {label} workspace module */

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
    color: var(--color-fg-default, #c9d1d9);
    margin: 0 0 0.5rem;
}}

.{name}-subtitle {{
    font-size: 0.875rem;
    color: var(--color-fg-muted, #8b949e);
    margin: 0;
}}

.{name}-content {{
    background: var(--color-canvas-subtle, #161b22);
    border: 1px solid var(--color-border-default, #30363d);
    border-radius: 6px;
    padding: 2rem;
}}

.{name}-getting-started {{
    margin-bottom: 2rem;
}}

.{name}-getting-started h3 {{
    font-size: 1.125rem;
    color: var(--color-fg-default, #c9d1d9);
    margin: 0 0 1rem;
}}

.{name}-steps {{
    padding-left: 1.25rem;
    color: var(--color-fg-muted, #8b949e);
    line-height: 1.8;
}}

.{name}-steps code {{
    background: var(--color-canvas-default, #0d1117);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8125rem;
}}

.{name}-card {{
    background: var(--color-canvas-default, #0d1117);
    border: 1px solid var(--color-border-default, #30363d);
    border-radius: 6px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}}

.{name}-placeholder {{
    text-align: center;
    padding: 3rem 1rem;
    color: var(--color-fg-muted, #8b949e);
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
                "instructions": f"You are a helpful assistant for the {label} module.",
            }
        },
    }
    return json.dumps(config, indent=2) + "\n"


def _readme_md(name, label, description, license_id):
    desc = description or "A SciTeX App plugin."
    return f"""# {label}

{desc}

## Structure

```
{name}/
  __init__.py          # Module init
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
