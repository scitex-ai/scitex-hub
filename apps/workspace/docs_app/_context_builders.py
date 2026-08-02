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
    """Build Python packages context from ECOSYSTEM (source of truth)."""
    import importlib.metadata
    import logging

    from .views import check_docs_available

    logger = logging.getLogger(__name__)

    try:
        from scitex_dev.ecosystem import ECOSYSTEM
    except ImportError:
        logger.warning("scitex_dev.ecosystem not available — cannot list packages")
        return {"core_packages": [], "standalone_packages": []}

    # Packages to skip from docs listing (aliases, templates without docs)
    _SKIP_PACKAGES = {
        "scitex-plt",  # alias for figrecipe
        "automated-research-demo",  # template, no docs
        "scitex-research-template",  # template, no docs
        "pip-project-template",  # template, no docs
        "singularity-template",  # template, no docs
    }

    core_packages = []
    standalone_packages = []

    for pip_name, info in ECOSYSTEM.items():
        if pip_name in _SKIP_PACKAGES:
            continue

        module_name = info.get("import_name", pip_name.replace("-", "_"))

        try:
            meta = importlib.metadata.metadata(pip_name)
            version = meta["Version"] or ""
            description = meta.get("Summary", "")
            github_url = ""
            for url_entry in meta.get_all("Project-URL") or []:
                label, _, url = url_entry.partition(",")
                url = url.strip()
                if label.strip().lower() in ("homepage", "repository"):
                    github_url = url
                    break
        except importlib.metadata.PackageNotFoundError:
            logger.warning(
                "Package '%s' from ECOSYSTEM not installed — showing with limited info",
                pip_name,
            )
            version = ""
            description = ""
            github_url = ""

        github_repo = info.get("github_repo", "")
        if not github_url and github_repo:
            github_url = f"https://github.com/{github_repo}"

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

    return {
        "core_packages": core_packages,
        "standalone_packages": standalone_packages,
    }


def _resolve_doc_page(doc_base, page_file: str):
    """Resolve ``page_file`` inside ``doc_base``, or None if it escapes/is missing.

    Containment is COMPONENT-WISE (``resolve()`` then ``relative_to()``), never a
    string prefix match. A prefix match is not containment: ``/docs/pkg`` is a
    string prefix of the sibling ``/docs/pkg-private``, so ``startswith()`` would
    admit ``doc_base / "../pkg-private/secret"``. ``resolve()`` also collapses
    symlinks, so a link planted inside doc_base cannot step outside it.

    Returns None (never raises) so the caller falls back to index.html.
    """
    from pathlib import Path

    if not page_file or page_file.startswith("/") or ".." in Path(page_file).parts:
        return None
    try:
        target = (doc_base / page_file).resolve()
        target.relative_to(doc_base.resolve())
    except (ValueError, OSError, RuntimeError):
        return None
    return target if target.is_file() else None


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

    # Determine which page to show.
    #
    # SECURITY (card sec-docs-sphinx-page-traversal-latent-20260802): `sphinx_page`
    # is `?page=` straight off the request, and docs_content() carries no
    # @login_required — so it is attacker-controlled and unauthenticated. Joining it
    # onto doc_base unchecked is CWE-22 path traversal.
    # The old `.exists()` fallback was NOT a guard: it corrected an escape that
    # MISSED and happily read one that LANDED.
    page_file = sphinx_page or "index.html"
    target_path = _resolve_doc_page(doc_base, page_file)
    if target_path is None:
        page_file = "index.html"
        target_path = doc_base / page_file
        if not target_path.is_file():
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
