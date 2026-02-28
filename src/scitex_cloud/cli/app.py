#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI commands for app scaffold and management."""

import base64
import os

import click
import requests
from rich.console import Console

console = Console()

# Scaffold file templates (self-contained, no Django imports needed)
_SCAFFOLD_TEMPLATES = {
    "apps.py": (
        '"""Django app configuration for {label}."""\n\n'
        "from django.apps import AppConfig\n\n\n"
        "class {class_name}Config(AppConfig):\n"
        '    default_auto_field = "django.db.models.BigAutoField"\n'
        '    name = "{name}"\n'
        '    verbose_name = "{label}"\n'
    ),
    "views.py": (
        '"""Views for {label} workspace module."""\n\n'
        "from django.shortcuts import render\n\n\n"
        "def build_{name}_context(request, current_project=None):\n"
        '    """Context builder called by workspace registry."""\n'
        '    return {{"current_project": current_project}}\n\n\n'
        "def index(request):\n"
        '    """Standalone page view."""\n'
        "    context = build_{name}_context(request)\n"
        '    return render(request, "{name}/index.html", context)\n'
    ),
    "urls.py": (
        '"""URL configuration for {name}."""\n\n'
        "from django.urls import path\n"
        "from . import views\n\n"
        'app_name = "{name}"\n\n'
        "urlpatterns = [\n"
        '    path("", views.index, name="index"),\n'
        "]\n"
    ),
}


def _build_files(name, label):
    """Build scaffold file dict without Django dependency."""
    class_name = label.replace(" ", "")
    files = {}
    for filename, template in _SCAFFOLD_TEMPLATES.items():
        files[filename] = template.format(name=name, label=label, class_name=class_name)
    files[f"templates/{name}/index.html"] = (
        '{{% extends "global_base.html" %}}\n'
        "{{% block title %}}{label}{{% endblock %}}\n"
        "{{% block content %}}\n"
        '    {{% include "{name}/index_partial.html" %}}\n'
        "{{% endblock %}}\n"
    ).format(name=name, label=label)
    files[f"templates/{name}/index_partial.html"] = (
        f'<div class="{name}-container" style="padding: 20px;">\n'
        f'    <h2><i class="fas fa-puzzle-piece"></i> {label}</h2>\n'
        f"    <p>Welcome to {label}. Edit this template to build your app.</p>\n"
        f"</div>\n"
    )
    files[f"static/{name}/css/{name}.css"] = (
        f"/* Styles for {name} workspace module */\n\n"
        f".{name}-container {{\n"
        f"    max-width: 1200px;\n"
        f"    margin: 0 auto;\n"
        f"    padding: 20px;\n"
        f"}}\n"
    )
    files["README.md"] = f"# {label}\n\nA SciTeX Marketplace App.\n"
    return files


def _gitea_create_file(base_url, token, owner, repo, filepath, content, branch="main"):
    """Create a file in Gitea via REST API."""
    url = f"{base_url}/api/v1/repos/{owner}/{repo}/contents/{filepath}"
    resp = requests.post(
        url,
        json={
            "content": base64.b64encode(content.encode()).decode(),
            "message": f"scaffold: add {filepath}",
            "branch": branch,
        },
        headers={"Authorization": f"token {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@click.group()
def app():
    """Manage SciTeX marketplace apps."""


@app.command("init")
@click.argument("project_slug")
@click.option("--username", "-u", default=None, help="Project owner username")
@click.option("--app-name", "-n", default=None, help="App name (defaults to slug)")
@click.option("--branch", "-b", default="main", help="Target branch")
def app_init(project_slug, username, app_name, branch):
    """Initialize app template files in a project.

    Scaffolds apps.py, views.py, urls.py, templates, static, and README
    in the project's Gitea repository.

    \b
    Requires environment variables:
        GITEA_URL      - Gitea instance URL (default: http://localhost:3001)
        GITEA_TOKEN    - API token for authentication
        GITEA_USERNAME - Default owner (or use --username)

    \b
    Examples:
        scitex-cloud app init my-project
        scitex-cloud app init my-project -u johndoe
        scitex-cloud app init my-project -n custom_name
    """
    base_url = os.environ.get("GITEA_URL", "http://localhost:3001")
    token = os.environ.get("GITEA_TOKEN", "")
    owner = username or os.environ.get("GITEA_USERNAME", "")

    if not owner:
        console.print(
            "[red]Error:[/red] No username. Use --username or set GITEA_USERNAME."
        )
        raise SystemExit(1)
    if not token:
        console.print(
            "[red]Error:[/red] No token. Set GITEA_TOKEN environment variable."
        )
        raise SystemExit(1)

    name = app_name or project_slug.replace("-", "_")
    label = name.replace("_", " ").title()
    files = _build_files(name, label)

    console.print(f"[cyan]Scaffolding app for[/cyan] {owner}/{project_slug}...")

    created = []
    for filepath, content in files.items():
        try:
            _gitea_create_file(
                base_url, token, owner, project_slug, filepath, content, branch
            )
            created.append(filepath)
            console.print(f"  [green]+[/green] {filepath}")
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 422:
                console.print(f"  [yellow]~[/yellow] {filepath} (already exists)")
            else:
                console.print(f"  [yellow]~[/yellow] {filepath} (error: {exc})")
        except Exception as exc:
            console.print(f"  [yellow]~[/yellow] {filepath} (error: {exc})")

    console.print(
        f"\n[green]Done![/green] Scaffolded {len(created)}/{len(files)} files."
    )


# EOF
