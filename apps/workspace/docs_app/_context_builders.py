#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Context builders for documentation pages.

Extracted from views.py to keep it under the file size limit.
"""


def build_page_context(slug: str) -> dict:
    """Build template context for a documentation page."""
    context = {
        "slug": slug,
        "base_template": "docs_app/docs_fragment_base.html",
    }
    if slug in ("mcp-tools-local", "mcp-tools-https", "api-mcp"):
        context.update(_get_mcp_context())
    elif slug == "python-packages":
        context.update(_get_packages_context())
    return context


def _get_packages_context() -> dict:
    """Build Python packages context dynamically from scitex_dev.docs entry points."""
    from .views import check_docs_available

    try:
        from scitex_dev._discovery import discover_packages, get_package_metadata
    except ImportError:
        return {"core_packages": [], "standalone_packages": []}

    discovered = discover_packages()

    core_packages = []
    standalone_packages = []

    for pip_name in sorted(discovered):
        meta = get_package_metadata(pip_name)
        if meta is None:
            continue

        repo = meta["github_repo"]
        # Use pip_name for internal routing (sphinx_url, check_docs_available)
        # since _resolve_sphinx_path maps via _REPO_TO_PIP
        has_sphinx = check_docs_available(pip_name)

        pkg = {
            "pip_name": pip_name,
            "module": meta["module_name"],
            "version": meta["version"],
            "description": meta["description"],
            "github_url": meta["github_url"]
            or f"https://github.com/ywatanabe1989/{repo}",
            "docs_url": f"https://{pip_name}.readthedocs.io",
            "sphinx_url": (
                f"/apps/docs/sphinx/{pip_name}/index.html" if has_sphinx else ""
            ),
            "has_sphinx": has_sphinx,
            "pypi_version": meta["version"],
            "status": "",
        }

        if meta["is_core"]:
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
            "docs_url": "https://scitex-cloud.readthedocs.io",
            "sphinx_url": (
                "/apps/docs/sphinx/scitex-cloud/index.html" if has_sphinx else ""
            ),
            "has_sphinx": has_sphinx,
            "pypi_version": "",
            "status": "",
        }
    )


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
