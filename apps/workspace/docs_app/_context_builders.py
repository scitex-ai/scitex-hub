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
    if slug == "overview" or slug.startswith("api-"):
        from apps.infra.public_app.services.interface_catalog import (
            build_interface_catalog,
        )

        context["interface_catalog"] = build_interface_catalog()
    elif slug in ("mcp-tools-local", "mcp-tools-https", "api-mcp"):
        context.update(_get_mcp_context())
    elif slug == "python-packages":
        context.update(_get_packages_context())
    elif slug.startswith("pkg-"):
        context.update(_get_sphinx_package_context(slug, sphinx_page))
    return context


def _get_packages_context() -> dict:
    """Project the same registered documentation owners used by the overview."""
    import importlib.metadata
    from urllib.parse import urlsplit

    from apps.infra.public_app.services.interface_catalog import build_interface_catalog

    catalog = build_interface_catalog()
    core, standalone = [], []
    for row in catalog["packages"]:
        if not row["docs"]:
            continue
        provider = next((d for d in row["docs"] if d["state"] == "registered"), None)
        github_url = ""
        try:
            meta = importlib.metadata.metadata(row["distribution"])
            for value in meta.get_all("Project-URL") or []:
                label, _, url = value.partition(",")
                parsed = urlsplit(url.strip())
                if (
                    label.strip().lower() in {"homepage", "repository"}
                    and parsed.scheme in {"http", "https"}
                    and parsed.hostname
                    and not parsed.username
                ):
                    github_url = url.strip()
                    break
        except importlib.metadata.PackageNotFoundError:
            pass
        pkg = {
            "pip_name": row["distribution"],
            "module": provider["target"] if provider else "",
            "version": row["version"] or "",
            "description": row["summary"],
            "github_url": github_url,
            "docs_url": provider["url"] if provider else "",
            "sphinx_url": provider["url"] if provider else "",
            "has_sphinx": None,
            "pypi_version": "",
            "status": "registered" if provider else "ambiguous",
            "artifact_availability": "not_checked",
            "api_docs_url": row["api_docs_url"],
        }
        (core if row["distribution"].startswith("scitex") else standalone).append(pkg)
    return {
        "core_packages": core,
        "standalone_packages": standalone,
        "provider_discovery": catalog["docs_discovery"],
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
    from apps.infra.platform_app.services.paths import resolve_within

    if not page_file or page_file.startswith("/"):
        return None
    target = resolve_within(doc_base, page_file)
    if target is None:
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
        from apps.infra.platform_app.services.paths import resolve_within

        target_path = resolve_within(doc_base, page_file)
        if target_path is None:
            return {"doc_content": "<p>Documentation not built yet.</p>"}
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
