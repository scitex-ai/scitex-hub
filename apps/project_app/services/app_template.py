#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App template scaffolding — creates required files for an app in Gitea."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def create_app_from_template(project, app_name=None):
    """Scaffold required app files in a project's Gitea repo.

    Creates: apps.py, views.py, urls.py, templates, static, agents config, README.
    Uses existing GiteaClient.create_file() for each file.

    Returns list of created file paths, or raises on failure.
    """
    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()
    owner = project.owner.username
    repo = project.slug
    name = app_name or project.slug.replace("-", "_")
    label = name.replace("_", " ").title()

    files = _build_scaffold_files(name, label)
    created = []

    for filepath, content in files.items():
        try:
            client.create_file(
                owner=owner,
                repo=repo,
                filepath=filepath,
                content=content,
                message=f"scaffold: add {filepath}",
                branch="main",
            )
            created.append(filepath)
        except Exception as e:
            # File may already exist — skip
            logger.debug("[app_template] Skipped %s: %s", filepath, e)

    logger.info(
        "[app_template] Scaffolded %d/%d files for %s/%s",
        len(created),
        len(files),
        owner,
        repo,
    )
    return created


def _build_scaffold_files(name, label):
    """Build dict of filepath -> content for app scaffold."""
    return {
        "apps.py": _apps_py(name, label),
        "views.py": _views_py(name, label),
        "urls.py": _urls_py(name),
        f"templates/{name}/index.html": _index_html(name, label),
        f"templates/{name}/index_partial.html": _index_partial_html(name, label),
        f"static/{name}/css/{name}.css": _app_css(name),
        ".agents/agents.json": _agents_json(name),
        "README.md": _readme_md(name, label),
    }


def _apps_py(name, label):
    return f'''"""Django app configuration for {label}."""

from django.apps import AppConfig


class {label.replace(" ", "")}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{name}"
    verbose_name = "{label}"
'''


def _views_py(name, label):
    return f'''"""Views for {label} workspace module."""

from django.shortcuts import render


def build_{name}_context(request, current_project=None):
    """Context builder called by workspace registry."""
    return {{"current_project": current_project}}


def index(request):
    """Standalone page view."""
    context = build_{name}_context(request)
    return render(request, "{name}/index.html", context)
'''


def _urls_py(name):
    return f'''"""URL configuration for {name}."""

from django.urls import path
from . import views

app_name = "{name}"

urlpatterns = [
    path("", views.index, name="index"),
]
'''


def _index_html(name, label):
    return f"""{{% extends "global_base.html" %}}
{{% block title %}}{label}{{% endblock %}}
{{% block content %}}
    {{% include "{name}/index_partial.html" %}}
{{% endblock %}}
"""


def _index_partial_html(name, label):
    return f"""<div class="{name}-container" style="padding: 20px;">
    <h2><i class="fas fa-puzzle-piece"></i> {label}</h2>
    <p>Welcome to {label}. Edit this template to build your app.</p>
</div>
"""


def _app_css(name):
    return f"""/* Styles for {name} workspace module */

.{name}-container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}}
"""


def _agents_json(name):
    return f"""{{
    "version": 3,
    "agents": {{
        "default": {{
            "name": "{name}-agent",
            "model": "claude-sonnet-4-20250514",
            "instructions": "You are a helpful assistant for the {name} module."
        }}
    }}
}}
"""


def _readme_md(name, label):
    return f"""# {label}

A SciTeX App.

## Structure

- `apps.py` — Django app config
- `views.py` — View functions and context builder
- `urls.py` — URL routing
- `templates/{name}/` — HTML templates
- `static/{name}/css/` — Stylesheets
- `.agents/` — AI agent configuration

## Development

1. Edit templates and views to build your app
2. Test locally in the SciTeX workspace
3. Submit to the Apps catalog when ready

## License

See `LICENSE` file.
"""


# EOF
