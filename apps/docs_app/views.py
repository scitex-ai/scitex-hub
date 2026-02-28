#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/views.py

from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

# ---------------------------------------------------------------------------
# Documentation page registry — single source of truth for sidebar + content
# ---------------------------------------------------------------------------
DOCS_PAGES = [
    {
        "slug": "python-packages",
        "label": "Python Packages",
        "icon": "fas fa-cube",
        "template": "docs_app/docs_python_packages.html",
        "badges": ["user"],
    },
    {
        "slug": "mcp-tools-local",
        "label": "MCP Tools (Local)",
        "icon": "fas fa-desktop",
        "template": "docs_app/docs_mcp_tools_local.html",
        "badges": ["user"],
    },
    {
        "slug": "mcp-tools-https",
        "label": "MCP Tools (Https)",
        "icon": "fas fa-cloud",
        "template": "docs_app/docs_mcp_tools_https.html",
        "badges": ["user"],
    },
    {
        "slug": "ssh-access",
        "label": "SSH Access",
        "icon": "fas fa-terminal",
        "template": "docs_app/docs_ssh.html",
        "badges": ["user"],
    },
    {
        "slug": "app-maker",
        "label": "App Maker",
        "icon": "fas fa-puzzle-piece",
        "template": "docs_app/docs_app_maker.html",
        "badges": ["user"],
    },
    {
        "slug": "agpl-v3",
        "label": "AGPL v3.0",
        "icon": "fas fa-balance-scale",
        "template": "docs_app/docs_agpl.html",
        "badges": [],
    },
    {
        "slug": "web-api",
        "label": "Web API",
        "icon": "fas fa-plug",
        "template": "docs_app/docs_api_content.html",
        "badges": ["user", "dev"],
    },
    {
        "slug": "app-maker-creators",
        "label": "App Maker",
        "icon": "fas fa-code",
        "template": "docs_app/docs_app_maker_creators.html",
        "badges": ["user", "dev"],
    },
    {
        "slug": "plugin-license",
        "label": "Licensing",
        "icon": "fas fa-file-contract",
        "template": "docs_app/docs_plugin_license.html",
        "badges": ["user", "dev"],
    },
    {
        "slug": "self-hosting",
        "label": "Self-Hosting",
        "icon": "fas fa-server",
        "template": "docs_app/docs_self_hosting.html",
        "badges": ["admin"],
    },
    {
        "slug": "app-maker-admins",
        "label": "App Maker",
        "icon": "fas fa-cog",
        "template": "docs_app/docs_app_maker_admins.html",
        "badges": ["admin"],
    },
]

_PAGES_BY_SLUG = {p["slug"]: p for p in DOCS_PAGES}


# ---------------------------------------------------------------------------
# Context builder (called by workspace registry)
# ---------------------------------------------------------------------------
def build_docs_context(request, current_project=None):
    """Build context for the docs workspace partial."""
    return {
        "current_project": current_project,
        "docs_pages": DOCS_PAGES,
        "active_doc": DOCS_PAGES[0]["slug"] if DOCS_PAGES else "",
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def docs_index(request):
    """Documentation landing page (standalone, outside workspace)."""
    context = {
        "modules": [
            {
                "name": "Python Package",
                "slug": "python",
                "description": "SciTeX Python package (pip install scitex)",
                "icon": "scitex_logos/scitex-icons/scitex-icon-navy.svg",
                "available": _check_docs_available("python"),
            },
            {
                "name": "REST API",
                "slug": "api",
                "description": "REST API reference for SciTeX Cloud",
                "icon": "scitex_logos/scitex-icons/scitex-icon-navy.svg",
                "available": True,
            },
        ]
    }
    return render(request, "docs_app/docs_index.html", context)


def docs_content(request, slug):
    """Serve a documentation fragment via AJAX for the workspace partial."""
    page = _PAGES_BY_SLUG.get(slug)
    if not page:
        raise Http404(f"Documentation page '{slug}' not found")
    return render(request, page["template"], {"slug": slug})


def docs_python(request):
    """Serve SciTeX Python package documentation (Sphinx)."""
    return _serve_sphinx_docs(request, "python", "index.html")


def docs_api(request):
    """Serve REST API documentation page."""
    return render(request, "public_app/pages/api_docs.html")


def docs_page(request, module, page):
    """Serve a specific Sphinx documentation page."""
    return _serve_sphinx_docs(request, module, page)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DOC_PATHS = {
    "python": "../scitex-code/docs/sphinx/build/html",
}


def _check_docs_available(module):
    """Check if Sphinx documentation is built for a module."""
    if module not in DOC_PATHS:
        return False
    doc_path = Path(settings.BASE_DIR) / DOC_PATHS[module]
    return doc_path.exists() and (doc_path / "index.html").exists()


def _serve_sphinx_docs(request, module, page="index.html"):
    """Serve Sphinx-built documentation files."""
    if module not in DOC_PATHS:
        raise Http404("Module documentation not found")

    doc_base = Path(settings.BASE_DIR) / DOC_PATHS[module]
    doc_file = doc_base / page

    if not doc_base.exists() or not doc_file.exists():
        github_urls = {
            "python": "https://github.com/ywatanabe1989/SciTeX-Code#readme",
        }
        return redirect(github_urls.get(module, "https://github.com/SciTeX-AI"))

    # Security: ensure path stays within documentation directory
    try:
        doc_file = doc_file.resolve()
        doc_base = doc_base.resolve()
        if not str(doc_file).startswith(str(doc_base)):
            raise Http404("Invalid documentation path")
    except (ValueError, OSError):
        raise Http404("Invalid documentation path")

    if doc_file.suffix == ".html":
        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()
        context = {
            "module": module,
            "module_name": module.capitalize(),
            "doc_content": content,
            "page": page,
        }
        return render(request, "docs_app/docs_page.html", context)
    else:
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
        }
        content_type = content_types.get(doc_file.suffix, "application/octet-stream")
        with open(doc_file, "rb") as f:
            return HttpResponse(f.read(), content_type=content_type)
