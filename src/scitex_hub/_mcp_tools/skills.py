#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/skills.py
"""Skills MCP tools — required §5 skills-integration surface.

Mirrors `scitex-hub skills list` / `scitex-hub skills get`: walks the
package's own bundled `_skills/scitex-hub/` directory (no scitex-dev
runtime dependency), so any MCP consumer can discover and read the
agent-facing skills this package ships.
"""

from __future__ import annotations

from pathlib import Path

from .api import _json

_PKG = "scitex-hub"


def _skills_root() -> Path:
    """Resolve the bundled `_skills/scitex-hub/` directory."""
    import scitex_hub

    return Path(scitex_hub.__file__).parent / "_skills" / _PKG


def _list_skill_files(root: Path) -> list[Path]:
    """All `.md` files under the skills root (recursive), excluding SKILL.md."""
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*.md") if p.is_file() and p.name != "SKILL.md"
    )


def register_skills_tools(mcp) -> None:
    """Register the required skills tools with the FastMCP server."""

    @mcp.tool()
    async def hub_skills_list() -> str:
        """Use when an agent needs to discover the skill files bundled with scitex-hub; mirrors `scitex-hub skills list --json` (name + path per skill, SKILL.md excluded)."""
        root = _skills_root()
        files = _list_skill_files(root)
        return _json(
            {
                "success": True,
                "count": len(files),
                "skills": [
                    {"name": p.stem, "path": str(p.relative_to(root))}
                    for p in files
                ],
            }
        )

    @mcp.tool()
    async def hub_skills_get(name: str) -> str:
        """Use when an agent needs the full text of one bundled scitex-hub skill file by stem name (e.g. "01_installation"); mirrors `scitex-hub skills get <name> --json`.

        Args:
            name: Skill stem name, with or without the `.md` extension.
        """
        root = _skills_root()
        target_stem = name[:-3] if name.endswith(".md") else name
        match = next(
            (p for p in _list_skill_files(root) if p.stem == target_stem), None
        )
        if match is None:
            return _json(
                {
                    "success": False,
                    "error": f"skill not found: {name}",
                    "available": [p.stem for p in _list_skill_files(root)],
                }
            )
        return _json(
            {
                "success": True,
                "name": match.stem,
                "path": str(match),
                "content": match.read_text(encoding="utf-8"),
            }
        )


# EOF
