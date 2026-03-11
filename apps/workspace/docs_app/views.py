#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/views.py

from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from ._context_builders import build_page_context

# ---------------------------------------------------------------------------
# Documentation page registry — single source of truth for sidebar + content
# ---------------------------------------------------------------------------
DOCS_PAGES = [
    # ── Getting Started ─────────────────────────────────────────────
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
        "slug": "console",
        "label": "Console",
        "icon": "fas fa-terminal",
        "template": "docs_app/docs_console.html",
        "badges": ["user"],
    },
    # ── AI Features ─────────────────────────────────────────────────
    {
        "slug": "chat",
        "label": "AI Chat",
        "icon": "fas fa-comments",
        "template": "docs_app/docs_chat.html",
        "badges": ["user"],
    },
    {
        "slug": "agent",
        "label": "Agent Integration",
        "icon": "fas fa-robot",
        "template": "docs_app/docs_agent.html",
        "badges": ["user"],
    },
    {
        "slug": "agent-tooling",
        "label": "AI Agent Tooling",
        "icon": "fas fa-tools",
        "template": "docs_app/docs_agent_tooling.html",
        "badges": ["user"],
    },
    {
        "slug": "auto-response",
        "label": "Auto-Response",
        "icon": "fas fa-reply",
        "template": "docs_app/docs_auto_response.html",
        "badges": ["user"],
    },
    # ── Developer Reference ─────────────────────────────────────────
    {
        "slug": "app-development",
        "label": "App Development",
        "icon": "fas fa-puzzle-piece",
        "template": "docs_app/docs_app_development.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-getting-started",
        "label": "API: Getting Started",
        "icon": "fas fa-rocket",
        "template": "docs_app/docs_api_getting_started.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-scholar",
        "label": "API: Scholar",
        "icon": "fas fa-book",
        "template": "docs_app/docs_api_scholar.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-plot",
        "label": "API: Plot",
        "icon": "fas fa-chart-bar",
        "template": "docs_app/docs_api_plot.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-stats",
        "label": "API: Stats",
        "icon": "fas fa-calculator",
        "template": "docs_app/docs_api_stats.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-writer",
        "label": "API: Writer",
        "icon": "fas fa-pen",
        "template": "docs_app/docs_api_writer.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-project",
        "label": "API: Project",
        "icon": "fas fa-folder",
        "template": "docs_app/docs_api_project.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-mcp",
        "label": "API: MCP Server",
        "icon": "fas fa-robot",
        "template": "docs_app/docs_api_mcp.html",
        "badges": ["dev"],
    },
    {
        "slug": "api-resources",
        "label": "API: Resources",
        "icon": "fas fa-archive",
        "template": "docs_app/docs_api_resources.html",
        "badges": ["dev"],
    },
    {
        "slug": "design-rules",
        "label": "Design Rules",
        "icon": "fas fa-ruler-combined",
        "template": "docs_app/docs_design_rules.html",
        "badges": ["dev"],
    },
    {
        "slug": "shared-ts-components",
        "label": "Shared: Components",
        "icon": "fas fa-cubes",
        "template": "docs_app/docs_shared_ts_components.html",
        "badges": ["dev"],
    },
    {
        "slug": "shared-ts-utilities",
        "label": "Shared: Utilities",
        "icon": "fas fa-toolbox",
        "template": "docs_app/docs_shared_ts_utilities.html",
        "badges": ["dev"],
    },
    {
        "slug": "shared-css-system",
        "label": "Shared: CSS System",
        "icon": "fas fa-paint-brush",
        "template": "docs_app/docs_shared_css_system.html",
        "badges": ["dev"],
    },
    {
        "slug": "visitor-lifecycle",
        "label": "Visitor Lifecycle",
        "icon": "fas fa-user-clock",
        "template": "docs_app/docs_visitor_lifecycle.html",
        "badges": ["dev"],
    },
    # ── Administration ──────────────────────────────────────────────
    {
        "slug": "self-hosting",
        "label": "Self-Hosting",
        "icon": "fas fa-server",
        "template": "docs_app/docs_self_hosting.html",
        "badges": ["admin"],
    },
    # ── Legal ───────────────────────────────────────────────────────
    {
        "slug": "agpl-v3",
        "label": "AGPL v3.0",
        "icon": "fas fa-balance-scale",
        "template": "docs_app/docs_agpl.html",
        "badges": [],
    },
]

_PAGES_BY_SLUG = {p["slug"]: p for p in DOCS_PAGES}


def register_module_docs():
    """Auto-register docs pages for workspace modules that have docs_slug set.

    Scans all registered modules. For each module with a non-empty docs_slug,
    checks if a template exists at ``{app_name}/docs/{docs_slug}.html``.
    If found, appends it to DOCS_PAGES so it appears in the Docs sidebar.
    """
    from django.template.loader import get_template

    from apps.infra.workspace_app.registry import get_all_modules

    for mod in get_all_modules():
        if not mod.docs_slug:
            continue
        if mod.docs_slug in _PAGES_BY_SLUG:
            continue  # Already registered
        template_path = f"{mod.app_name}/docs/{mod.docs_slug}.html"
        try:
            get_template(template_path)
        except Exception:
            continue  # Template doesn't exist, skip

        icon = mod.icon_fa if mod.icon_fa else "fas fa-puzzle-piece"
        page = {
            "slug": mod.docs_slug,
            "label": mod.label,
            "icon": icon,
            "template": template_path,
            "badges": ["app"],
        }
        DOCS_PAGES.append(page)
        _PAGES_BY_SLUG[mod.docs_slug] = page


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
    context = build_page_context(slug)
    return render(request, page["template"], context)


def docs_export(request, slug):
    """Export documentation as Markdown. Use slug='all' for all pages."""
    ver = _get_project_version()

    if slug == "all":
        markdown = _export_all_pages(request, ver)
        filename = f"scitex-cloud-v{ver}-docs-all.md"
    else:
        page = _PAGES_BY_SLUG.get(slug)
        if not page:
            raise Http404(f"Documentation page '{slug}' not found")
        markdown = _export_single_page(request, page)
        filename = f"scitex-cloud-v{ver}-docs-{slug}.md"

    response = HttpResponse(markdown, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def docs_export_batch(request):
    """Export selected documentation pages as Markdown (POST {slugs: [...]})."""
    import json

    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        slugs = json.loads(request.body).get("slugs", [])
    except (json.JSONDecodeError, AttributeError):
        return HttpResponse("Invalid JSON", status=400)
    if not slugs:
        return HttpResponse("Missing slugs", status=400)

    ver = _get_project_version()
    converter = _make_html2text()
    parts = [f"# SciTeX Documentation (v{ver}) — Selected Pages\n"]
    for slug in slugs:
        page = _PAGES_BY_SLUG.get(slug)
        if not page:
            continue
        html = render(
            request, page["template"], build_page_context(slug)
        ).content.decode()
        parts.append(f"\n---\n\n## {page['label']}\n\n{converter.handle(html)}")

    resp = HttpResponse("\n".join(parts), content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = (
        f'attachment; filename="scitex-cloud-v{ver}-docs-selected.md"'
    )
    return resp


def _export_single_page(request, page) -> str:
    """Render a single doc page to Markdown."""
    converter = _make_html2text()
    context = build_page_context(page["slug"])
    html = render(request, page["template"], context).content.decode()
    md = converter.handle(html)
    return f"# {page['label']}\n\n{md}"


def _export_all_pages(request, ver) -> str:
    """Render all doc pages into a single Markdown document."""
    converter = _make_html2text()
    parts = [f"# SciTeX Documentation (v{ver})\n"]
    for page in DOCS_PAGES:
        context = build_page_context(page["slug"])
        html = render(request, page["template"], context).content.decode()
        md = converter.handle(html)
        parts.append(f"\n---\n\n## {page['label']}\n\n{md}")
    return "\n".join(parts)


def _make_html2text():
    """Create a configured html2text converter."""
    import html2text

    converter = html2text.HTML2Text()
    converter.body_width = 80
    converter.ignore_links = False
    converter.ignore_images = False
    converter.protect_links = True
    converter.wrap_links = False
    return converter


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
def _get_project_version() -> str:
    """Read version from pyproject.toml (single source of truth)."""
    try:
        toml_path = Path(settings.BASE_DIR) / "pyproject.toml"
        for line in toml_path.read_text().splitlines():
            if line.startswith("version"):
                return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    return "unknown"


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
