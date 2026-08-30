#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/skills.py
"""Expose hub's bundled skill documents over MCP.

Hub ships 28 skill leaves under ``src/scitex_hub/_skills/scitex-hub/`` and,
until now, no way for an agent to read them without knowing the on-disk path.
audit-mcp-tools §5 requires every package with an MCP surface to publish
``<short>_skills_list`` / ``<short>_skills_get``; hub was missing both.

WRITTEN AS REAL FUNCTIONS, NOT CLOSURES — deliberately.

Every other tool module here registers nested ``@mcp.tool()`` closures inside
its ``register_*_tools(mcp)``. That shape is why audit-mcp-tools §6 reports
52 of hub's ~55 tools as having "no matching Python API": a closure defined
inside a register function is not importable, so nothing can pair with it.
The two functions below are module-level and importable, and the tools are
thin wrappers over them — so this module adds MCP surface WITHOUT adding to
that debt, and shows the shape the §6 campaign will move the rest toward.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["skills_dir", "skills_list", "skills_get", "register_skills_tools"]

_SKILLS_REL = Path("_skills") / "scitex-hub"


def skills_dir() -> Path:
    """Absolute path of the bundled skills directory."""
    return Path(__file__).resolve().parent.parent / _SKILLS_REL


def skills_list() -> list[str]:
    """Names of the bundled skill files, sorted.

    Returns the file STEMS (``01_installation``), not full filenames, so a
    caller passes the same token straight back to :func:`skills_get`. An
    absent directory returns ``[]`` rather than raising: a package with no
    skills is a valid package, and this is a discovery call.
    """
    directory = skills_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.md"))


def skills_get(name: str) -> dict:
    """Return one bundled skill document by stem name.

    ``name`` is matched against the file stem; a trailing ``.md`` is accepted
    and stripped so both forms work. Returns ``{"name", "content"}`` on a hit
    and ``{"name", "error", "available"}`` on a miss — the miss carries the
    valid names so a wrong guess is self-correcting rather than a dead end.

    The resolved path is confirmed to sit inside the skills directory before
    it is read, so a traversal token in ``name`` (``../../etc/passwd``)
    cannot reach outside the bundle.
    """
    stem = name[:-3] if name.endswith(".md") else name
    directory = skills_dir()
    candidate = (directory / f"{stem}.md").resolve()
    if directory.resolve() not in candidate.parents or not candidate.is_file():
        return {"name": name, "error": "not found", "available": skills_list()}
    return {"name": stem, "content": candidate.read_text(encoding="utf-8")}


def register_skills_tools(mcp) -> None:
    """Register the §5-required skills tools with the FastMCP server."""

    @mcp.tool()
    def hub_skills_list() -> str:
        """List the scitex-hub skill documents bundled with this package."""
        return json.dumps(skills_list(), indent=2)

    @mcp.tool()
    def hub_skills_get(name: str) -> str:
        """Return the full text of one bundled scitex-hub skill document."""
        return json.dumps(skills_get(name), indent=2)


# EOF
