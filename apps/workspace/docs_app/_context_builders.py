#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Context builders for documentation pages.

Extracted from views.py to keep it under the file size limit.
"""


def build_page_context(slug: str, sphinx_page: str = None) -> dict:
    """Build template context for a documentation page."""
    context = {
        "slug": slug,
        "base_template": "docs_app/docs_fragment_base.html",
    }
    if slug in ("mcp-tools-local", "mcp-tools-https", "api-mcp"):
        context.update(_get_mcp_context())
    elif slug == "python-packages":
        context.update(_get_packages_context())
    elif slug.startswith("pkg-"):
        context.update(_get_sphinx_package_context(slug, sphinx_page))
    return context


def _get_packages_context() -> dict:
    """Build Python packages context dynamically from scitex_dev.docs entry points."""
    import importlib.metadata

    from .views import check_docs_available

    try:
        from scitex_dev._discovery import discover_packages
    except ImportError:
        return {"core_packages": [], "standalone_packages": []}

    discovered = discover_packages()

    core_packages = []
    standalone_packages = []

    # Core packages are scitex-* prefixed (the ecosystem)
    _CORE_PREFIXES = ("scitex-", "scitex")

    for pip_name, module_name in sorted(discovered.items()):
        try:
            meta = importlib.metadata.metadata(pip_name)
        except importlib.metadata.PackageNotFoundError:
            continue

        version = meta["Version"] or ""
        description = meta.get("Summary", "")
        github_url = ""
        for url_entry in meta.get_all("Project-URL") or []:
            label, _, url = url_entry.partition(",")
            url = url.strip()
            if label.strip().lower() in ("homepage", "repository"):
                github_url = url
                break

        has_sphinx = check_docs_available(pip_name)

        pkg = {
            "pip_name": pip_name,
            "module": module_name,
            "version": version,
            "description": description,
            "github_url": github_url or f"https://github.com/ywatanabe1989/{pip_name}",
            "docs_url": f"/apps/docs/#pkg-{pip_name}",
            "sphinx_url": (
                f"/apps/docs/sphinx/{pip_name}/index.html" if has_sphinx else ""
            ),
            "has_sphinx": has_sphinx,
            "pypi_version": version,
            "status": "",
        }

        is_core = pip_name == "scitex" or pip_name.startswith("scitex-")
        if is_core:
            core_packages.append(pkg)
        else:
            standalone_packages.append(pkg)

    # scitex-cloud is the Django project itself, not a pip package
    _add_scitex_cloud(core_packages)

    return {
        "core_packages": core_packages,
        "standalone_packages": standalone_packages,
    }


def _add_scitex_cloud(core_packages: list) -> None:
    """Add scitex-cloud entry (not a pip package, requires special handling)."""
    from .views import check_docs_available

    has_sphinx = check_docs_available("scitex-cloud")
    try:
        from pathlib import Path

        from django.conf import settings

        toml_path = Path(settings.BASE_DIR) / "pyproject.toml"
        version = ""
        for line in toml_path.read_text().splitlines():
            if line.startswith("version"):
                version = line.split("=")[1].strip().strip('"')
                break
    except Exception:
        version = ""

    core_packages.append(
        {
            "pip_name": "scitex-cloud",
            "module": "scitex.cloud",
            "version": version,
            "description": "Django web application (this site)",
            "github_url": "https://github.com/ywatanabe1989/scitex-cloud",
            "docs_url": "/apps/docs/#pkg-scitex-cloud",
            "sphinx_url": (
                "/apps/docs/sphinx/scitex-cloud/index.html" if has_sphinx else ""
            ),
            "has_sphinx": has_sphinx,
            "pypi_version": "",
            "status": "",
        }
    )


def _get_sphinx_package_context(slug: str, sphinx_page: str = None) -> dict:
    """Build context for an inline Sphinx package documentation page."""
    from ._sphinx import (
        extract_sphinx_body,
        extract_sphinx_toc,
        list_sphinx_pages,
        resolve_sphinx_path,
    )

    pip_name = slug.removeprefix("pkg-")
    doc_base = resolve_sphinx_path(pip_name)
    if doc_base is None:
        return {"doc_content": "<p>Documentation not available.</p>"}

    # Determine which page to show
    page_file = sphinx_page or "index.html"
    target_path = doc_base / page_file
    if not target_path.exists():
        target_path = doc_base / "index.html"
        page_file = "index.html"
    if not target_path.exists():
        return {"doc_content": "<p>Documentation not built yet.</p>"}

    html = target_path.read_text(encoding="utf-8")
    body = extract_sphinx_body(html, pip_name=pip_name)
    toc = extract_sphinx_toc(html)
    pages = list_sphinx_pages(pip_name)

    # Mark current page as active
    for pg in pages:
        if pg["filename"] == page_file:
            pg["active"] = True

    # Get package metadata
    version = ""
    description = ""
    try:
        import importlib.metadata

        meta = importlib.metadata.metadata(pip_name)
        version = meta["Version"] or ""
        description = meta.get("Summary", "")
    except Exception:
        pass

    return {
        "doc_content": body,
        "sphinx_toc": toc,
        "sphinx_pages": pages,
        "package_name": pip_name,
        "package_version": version,
        "package_description": description,
    }


def _get_mcp_context() -> dict:
    """Build MCP tools context from the scitex MCP server registry."""
    try:
        from apps.infra.public_app.config.mcp_tools import get_mcp_tools

        tools = get_mcp_tools()
        total = sum(c["count"] for c in tools)
        return {"mcp_tools": tools, "mcp_tool_count": total}
    except Exception:
        return {"mcp_tools": [], "mcp_tool_count": 0}


# EOF
