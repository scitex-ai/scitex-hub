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
    """Build Python packages context from scitex ecosystem versions."""
    try:
        from scitex._dev._versions._list import list_versions

        raw = list_versions()
    except Exception:
        raw = {}

    # Package metadata: (module_path, description, github_repo, is_core)
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

    from .views import check_docs_available

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
        has_sphinx = check_docs_available(repo)
        pkg = {
            "pip_name": pip_name,
            "module": module,
            "version": version,
            "description": desc,
            "github_url": f"https://github.com/ywatanabe1989/{repo}",
            "docs_url": f"https://{repo}.readthedocs.io",
            "sphinx_url": f"/apps/docs/sphinx/{repo}/index.html" if has_sphinx else "",
            "has_sphinx": has_sphinx,
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
        from apps.infra.public_app.config.mcp_tools import get_mcp_tools

        tools = get_mcp_tools()
        total = sum(c["count"] for c in tools)
        return {"mcp_tools": tools, "mcp_tool_count": total}
    except Exception:
        return {"mcp_tools": [], "mcp_tool_count": 0}


# EOF
