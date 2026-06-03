#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sphinx documentation helpers — resolution, serving, registration, extraction.

Extracted from views.py to stay under the file size limit.
"""

import re
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render

# Repo-name → pip-name mapping for packages where they differ.
_REPO_TO_PIP = {
    "scitex-python": "scitex",
}

# Content types for static assets
_STATIC_CONTENT_TYPES = {
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
    ".eot": "application/vnd.ms-fontobject",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


def resolve_sphinx_path(module: str) -> "Path | None":
    """Resolve the Sphinx HTML directory for a module (repo name).

    Uses scitex_dev.docs.get_docs() for dynamic resolution, with a
    local-project fallback for scitex-hub (not a pip package).
    """
    if module == "scitex-hub":
        doc_path = Path(settings.BASE_DIR) / "docs" / "sphinx" / "_build" / "html"
        return doc_path if doc_path.exists() else None

    pip_name = _REPO_TO_PIP.get(module, module)
    try:
        from scitex_dev.docs import get_docs

        result = get_docs(package=pip_name, format="html")
        if isinstance(result, Path) and result.exists():
            return result
    except (LookupError, ImportError):
        pass

    return None


def check_docs_available(module: str) -> bool:
    """Check if Sphinx documentation is built for a module."""
    doc_path = resolve_sphinx_path(module)
    if doc_path is None:
        return False
    return (doc_path / "index.html").exists()


def sphinx_raw(request, module, page="index.html"):
    """Serve raw Sphinx HTML for iframe embedding (no Django template wrapping)."""
    doc_base = resolve_sphinx_path(module)
    if doc_base is None:
        raise Http404("Module documentation not found")

    doc_file = doc_base / page

    try:
        doc_file = doc_file.resolve()
        doc_base_resolved = doc_base.resolve()
        if not str(doc_file).startswith(str(doc_base_resolved)):
            raise Http404("Invalid documentation path")
    except (ValueError, OSError):
        raise Http404("Invalid documentation path")

    if not doc_file.exists():
        raise Http404(f"Documentation page not found: {page}")

    if doc_file.suffix == ".html":
        content = doc_file.read_text(encoding="utf-8")
        return HttpResponse(content, content_type="text/html; charset=utf-8")

    ct = _STATIC_CONTENT_TYPES.get(doc_file.suffix, "application/octet-stream")
    return HttpResponse(doc_file.read_bytes(), content_type=ct)


def serve_sphinx_docs(request, module, page="index.html"):
    """Serve Sphinx-built documentation files wrapped in Django template."""
    doc_base = resolve_sphinx_path(module)
    if doc_base is None:
        raise Http404(f"Documentation not found for module '{module}'")

    doc_file = doc_base / page

    if not doc_file.exists():
        raise Http404(f"Documentation page not found: {module}/{page}")

    try:
        doc_file = doc_file.resolve()
        doc_base = doc_base.resolve()
        if not str(doc_file).startswith(str(doc_base)):
            raise Http404("Invalid documentation path")
    except (ValueError, OSError):
        raise Http404("Invalid documentation path")

    if doc_file.suffix == ".html":
        content = doc_file.read_text(encoding="utf-8")
        context = {
            "module": module,
            "module_name": module.capitalize(),
            "doc_content": content,
            "page": page,
        }
        return render(request, "docs_app/docs_page.html", context)

    ct = _STATIC_CONTENT_TYPES.get(doc_file.suffix, "application/octet-stream")
    return HttpResponse(doc_file.read_bytes(), content_type=ct)


def register_sphinx_packages(docs_pages, pages_by_slug):
    """Auto-register sidebar entries for ECOSYSTEM packages with Sphinx docs."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        from scitex_dev.ecosystem import ECOSYSTEM
    except ImportError:
        logger.warning("scitex_dev.ecosystem not available — cannot register packages")
        return

    # Packages to skip (aliases, templates without docs)
    _SKIP = {
        "scitex-plt",
        "automated-research-demo",
        "scitex-research-template",
        "pip-project-template",
        "singularity-template",
    }

    for pip_name in ECOSYSTEM:
        if pip_name in _SKIP:
            continue
        slug = f"pkg-{pip_name}"
        if slug in pages_by_slug:
            continue
        if not check_docs_available(pip_name):
            logger.warning("Package '%s' has no Sphinx docs available", pip_name)
            continue
        page = {
            "slug": slug,
            "label": pip_name,
            "icon": "fas fa-book",
            "template": "docs_app/docs_sphinx_package.html",
            "badges": ["pkg"],
            "group": "packages",
        }
        docs_pages.append(page)
        pages_by_slug[slug] = page


def extract_sphinx_body(html: str, pip_name: str = "") -> str:
    """Extract the main content body from a Sphinx HTML page.

    Looks for <div role="main"> ... </div> and returns just the inner content,
    stripping the RTD theme chrome (nav, footer, sidebar).
    """
    # Find <div role="main" ...>
    match = re.search(
        r'<div\s+role="main"[^>]*>\s*<div\s+itemprop="articleBody"[^>]*>',
        html,
    )
    if not match:
        # Fallback: look for just role="main"
        match = re.search(r'<div\s+role="main"[^>]*>', html)
        if not match:
            return html  # Return full HTML if structure unrecognized

    start = match.end()
    # Find the closing tags — count div nesting
    depth = 1 if "articleBody" not in match.group() else 2
    pos = start
    body = ""
    while pos < len(html) and depth > 0:
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                body = html[start:next_close].strip()
                break
            pos = next_close + 6

    if not body:
        body = html[start:].strip()

    # Rewrite image paths to go through Django's Sphinx static serving
    if pip_name:
        body = re.sub(
            r'(src|href)="(_images/[^"]+)"',
            rf'\1="/apps/docs/sphinx/{pip_name}/\2"',
            body,
        )
        body = re.sub(
            r'(src|href)="(_static/[^"]+)"',
            rf'\1="/apps/docs/sphinx/{pip_name}/\2"',
            body,
        )

    return body


def extract_sphinx_toc(html: str) -> str:
    """Extract the table of contents sidebar from Sphinx HTML."""
    match = re.search(
        r'<div\s+class="wy-menu\s+wy-menu-vertical"[^>]*>(.*?)</div>\s*</div>\s*</nav>',
        html,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return ""


def list_sphinx_pages(module: str) -> list:
    """List available HTML pages for a Sphinx-documented package."""
    import html as html_mod

    doc_base = resolve_sphinx_path(module)
    if doc_base is None:
        return []

    pages = []
    for html_file in sorted(doc_base.glob("*.html")):
        name = html_file.stem
        if name in ("genindex", "py-modindex", "search", "objects"):
            continue
        # Extract title from <title> tag
        try:
            content = html_file.read_text(encoding="utf-8")
            title_match = re.search(r"<title>(.*?)</title>", content)
            title = (
                title_match.group(1) if title_match else name.replace("_", " ").title()
            )
            # Decode HTML entities (e.g. &mdash; → —) then strip suffix
            title = html_mod.unescape(title)
            title = re.sub(r"\s*[—–]\s+.*$", "", title)
        except Exception:
            title = name.replace("_", " ").title()

        pages.append({"filename": html_file.name, "title": title, "active": False})

    return pages


# EOF
