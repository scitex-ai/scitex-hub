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
    {
        "slug": "design-rules",
        "label": "Design Rules",
        "icon": "fas fa-ruler-combined",
        "template": "docs_app/docs_design_rules.html",
        "badges": ["dev"],
    },
    {
        "slug": "visitor-lifecycle",
        "label": "Visitor Lifecycle",
        "icon": "fas fa-user-clock",
        "template": "docs_app/docs_visitor_lifecycle.html",
        "badges": ["dev"],
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
    """Documentation page — renders inside workspace layout with docs partial."""
    context = build_docs_context(request)
    return render(request, "docs_app/docs_index.html", context)


def docs_content(request, slug):
    """Serve a documentation fragment via AJAX for the workspace partial."""
    page = _PAGES_BY_SLUG.get(slug)
    if not page:
        raise Http404(f"Documentation page '{slug}' not found")
    context = _build_page_context(slug)
    return render(request, page["template"], context)


def docs_export(request, slug):
    """Export a documentation page as Markdown."""
    import html2text

    page = _PAGES_BY_SLUG.get(slug)
    if not page:
        raise Http404(f"Documentation page '{slug}' not found")

    context = _build_page_context(slug)
    html_content = render(request, page["template"], context).content.decode()

    converter = html2text.HTML2Text()
    converter.body_width = 80
    converter.ignore_links = False
    converter.ignore_images = False
    converter.protect_links = True
    converter.wrap_links = False
    markdown = converter.handle(html_content)

    # Prepend title
    title = page["label"]
    markdown = f"# {title}\n\n{markdown}"

    filename = f"scitex-docs-{slug}.md"
    response = HttpResponse(markdown, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _build_page_context(slug):
    """Build template context for a documentation page."""
    context = {
        "slug": slug,
        "base_template": "docs_app/docs_fragment_base.html",
    }
    if slug in ("mcp-tools-local", "mcp-tools-https"):
        context.update(_get_mcp_context())
    elif slug == "python-packages":
        context.update(_get_packages_context())
    return context


def _get_packages_context() -> dict:
    """Build Python packages context from scitex ecosystem versions."""
    try:
        from scitex._dev._versions._list import list_versions

        raw = list_versions()
    except Exception:
        raw = {}

    # Package metadata: (pip_name, module_path, description, github_repo, is_core)
    _PKG_META = {
        "scitex": (
            "scitex",
            "Main Python package with unified API for scientific research",
            "scitex-python",
            True,
        ),
        "scitex-cloud": (
            "scitex.cloud",
            "Django web application (this site)",
            "scitex-cloud",
            True,
        ),
        "figrecipe": (
            "scitex.plt",
            "Publication-ready matplotlib figures with auto CSV export",
            "figrecipe",
            False,
        ),
        "scitex-writer": (
            "scitex.writer",
            "LaTeX manuscript compilation with journal templates",
            "scitex-writer",
            False,
        ),
        "scitex-dataset": (
            "scitex.dataset",
            "Scientific dataset search across OpenNeuro, DANDI, PhysioNet",
            "scitex-dataset",
            False,
        ),
        "scitex-linter": (
            "scitex.linter",
            "SciTeX coding style linter for Python scripts",
            "scitex-linter",
            False,
        ),
        "crossref-local": (
            "scitex.scholar.crossref_scitex",
            "Local CrossRef database (167M+ papers)",
            "crossref-local",
            False,
        ),
        "openalex-local": (
            "scitex.scholar.openalex_scitex",
            "Local OpenAlex database (250M+ papers)",
            "openalex-local",
            False,
        ),
        "socialia": (
            "socialia",
            "Social media posting (Twitter/X, Bluesky)",
            "socialia",
            False,
        ),
        "scitex-container": (
            "scitex_container",
            "Apptainer/Singularity container definitions for SciTeX",
            "scitex-container",
            False,
        ),
        "scitex-tunnel": (
            "scitex_tunnel",
            "Secure SSH tunnel management for remote SciTeX services",
            "scitex-tunnel",
            False,
        ),
    }

    core_packages = []
    standalone_packages = []
    for pip_name, (module, desc, repo, is_core) in _PKG_META.items():
        info = raw.get(pip_name, {})
        local = info.get("local", {})
        remote = info.get("remote", {})
        version = (
            local.get("pyproject_toml")
            or local.get("installed")
            or remote.get("pypi")
            or ""
        )
        pkg = {
            "pip_name": pip_name,
            "module": module,
            "version": version,
            "description": desc,
            "github_url": f"https://github.com/ywatanabe1989/{repo}",
            "docs_url": f"https://{repo}.readthedocs.io",
            "pypi_version": remote.get("pypi", ""),
            "status": info.get("status", ""),
        }
        if is_core:
            core_packages.append(pkg)
        else:
            standalone_packages.append(pkg)

    return {
        "core_packages": core_packages,
        "standalone_packages": standalone_packages,
    }


def _get_mcp_context() -> dict:
    """Build MCP tools context from the scitex MCP server registry."""
    try:
        from apps.public_app.config.mcp_tools import get_mcp_tools

        tools = get_mcp_tools()
        total = sum(c["count"] for c in tools)
        return {"mcp_tools": tools, "mcp_tool_count": total}
    except Exception:
        return {"mcp_tools": [], "mcp_tool_count": 0}


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
