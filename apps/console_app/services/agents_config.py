#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-23"
# File: apps/console_app/services/agents_config.py

"""
Auto-generate AI tool configs for user projects.

- .agents/agents.json — unified config for agents CLI (github.com/amtiYo/agents)
- .claude/ — Claude Code settings (MCP server, skills)

Both are auto-generated on terminal connect and are idempotent (no-op if exists).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

AGENTS_SCHEMA_VERSION = 3


def _get_mcp_url() -> str:
    """Build the SciTeX MCP HTTP endpoint URL."""
    base = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return f"{base}/mcp"


def _build_agents_json(mcp_url: str) -> dict:
    """Build the .agents/agents.json content."""
    return {
        "schemaVersion": AGENTS_SCHEMA_VERSION,
        "instructions": {"path": "AGENTS.md"},
        "integrations": {
            "enabled": ["claude", "codex", "gemini", "cursor", "copilot_vscode"],
            "options": {
                "cursorAutoApprove": False,
                "antigravityGlobalSync": False,
            },
        },
        "syncMode": "source-only",
        "mcp": {
            "servers": {
                "scitex": {
                    "label": "SciTeX Cloud",
                    "description": "SciTeX scientific research platform — 145+ MCP tools for plotting, statistics, literature, writing, and more",
                    "transport": "http",
                    "url": mcp_url,
                    "headers": {"Authorization": "Token {{SCITEX_API_TOKEN}}"},
                    "requiredEnv": ["SCITEX_API_TOKEN"],
                    "enabled": True,
                }
            }
        },
        "lastSync": None,
    }


def _build_local_json(api_token: str) -> dict:
    """Build .agents/local.json with actual secrets."""
    return {
        "mcpServers": {"scitex": {"headers": {"Authorization": f"Token {api_token}"}}}
    }


def _build_agents_md(project_name: str) -> str:
    """Build a minimal AGENTS.md for the project."""
    return (
        f"# {project_name}\n\n"
        "SciTeX Cloud project with access to 145+ MCP tools.\n\n"
        "## Available Tools\n\n"
        "Run `agents sync` to push this config to your AI coding tool.\n"
        "The SciTeX MCP server provides: plotting (plt), statistics (stats),\n"
        "literature search (scholar/crossref/openalex), manuscript writing (writer),\n"
        "dataset access, and more.\n"
    )


def ensure_agents_config(
    project_path: str | Path,
    api_token: str | None = None,
    project_name: str = "SciTeX Project",
) -> bool:
    """
    Create .agents/ config if missing, pointing to SciTeX MCP server.

    Returns True if files were created, False if already existed.
    """
    project_path = Path(project_path)
    agents_dir = project_path / ".agents"
    config_file = agents_dir / "agents.json"

    if config_file.exists():
        return False

    mcp_url = _get_mcp_url()

    try:
        agents_dir.mkdir(parents=True, exist_ok=True)

        # agents.json — committable, uses {{PLACEHOLDER}} for secrets
        config_file.write_text(json.dumps(_build_agents_json(mcp_url), indent=2) + "\n")

        # local.json — gitignored, contains actual token
        if api_token:
            local_file = agents_dir / "local.json"
            local_file.write_text(
                json.dumps(_build_local_json(api_token), indent=2) + "\n"
            )

        # AGENTS.md — project description for AI tools
        agents_md = project_path / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text(_build_agents_md(project_name))

        # Ensure .agents/local.json is gitignored
        gitignore = project_path / ".gitignore"
        gitignore_line = ".agents/local.json"
        if gitignore.exists():
            content = gitignore.read_text()
            if gitignore_line not in content:
                with gitignore.open("a") as f:
                    f.write(f"\n# AI agent secrets\n{gitignore_line}\n")
        else:
            gitignore.write_text(f"# AI agent secrets\n{gitignore_line}\n")

        logger.info("Created .agents/ config for project at %s", project_path)
        return True

    except Exception:
        logger.exception("Failed to create .agents/ config at %s", project_path)
        return False


# ---------------------------------------------------------------------------
# Claude Code config (.claude/)
# ---------------------------------------------------------------------------

# Default MCP tool groups — all enabled
DEFAULT_MCP_GROUPS = [
    "PLT",
    "STATS",
    "SCHOLAR",
    "WRITER",
    "CLEW",
    "AUDIO",
    "DIAGRAM",
    "CAPTURE",
    "INTROSPECT",
    "TEMPLATE",
    "PROJECT",
    "DATASET",
    "DEV",
    "LINTER",
    "SOCIAL",
    "UI",
    "USAGE",
]


def _build_claude_settings(mcp_env: dict[str, str] | None = None) -> dict:
    """Build .claude/settings.json with local stdio MCP server."""
    env = {}
    if mcp_env:
        env = mcp_env
    else:
        # All groups enabled by default
        for group in DEFAULT_MCP_GROUPS:
            env[f"SCITEX_MCP_USE_{group}"] = "1"

    return {
        "mcpServers": {
            "scitex": {
                "command": "scitex",
                "args": ["mcp", "start"],
                "env": env,
            }
        }
    }


def _build_claude_skill() -> str:
    """Build Claude Code skill from the registered app skills."""
    try:
        from apps.llm_app.skills.export import export_claude_skill

        return export_claude_skill()
    except Exception:
        logger.exception("Failed to export Claude skill from registry")
        # Fallback: minimal skill
        return (
            "---\n"
            "name: scitex-cloud\n"
            "description: SciTeX Cloud research platform with MCP tools\n"
            "---\n\n"
            "# SciTeX Cloud\n\n"
            "Use `import scitex as stx` for scientific research.\n"
            "MCP tools available: plt, stats, scholar, writer, clew, audio, diagram.\n"
        )


def ensure_claude_config(
    user_data_dir: str | Path,
    project_path: str | Path | None = None,
    project_name: str = "SciTeX Project",
    mcp_env: dict[str, str] | None = None,
    force: bool = False,
) -> bool:
    """
    Create .claude/ config for Claude Code if missing.

    Sets up:
    - ~/.claude/settings.json — MCP server (local stdio scitex)
    - ~/.claude/skills/scitex-cloud/SKILL.md — platform skills
    - <project>/CLAUDE.md — project instructions (if project_path given)

    Args:
        force: If True, regenerate settings.json even if it exists
               (used when user changes MCP preferences).

    Returns True if files were created/updated, False if already existed.
    """
    user_data_dir = Path(user_data_dir)
    claude_dir = user_data_dir / ".claude"
    settings_file = claude_dir / "settings.json"

    if settings_file.exists() and not force:
        return False

    try:
        # .claude/settings.json — MCP server config
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps(_build_claude_settings(mcp_env), indent=2) + "\n"
        )

        # .claude/skills/scitex-cloud/SKILL.md — compiled skills
        skill_dir = claude_dir / "skills" / "scitex-cloud"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(_build_claude_skill())

        # Project-level CLAUDE.md
        if project_path:
            project_path = Path(project_path)
            claude_md = project_path / "CLAUDE.md"
            if not claude_md.exists():
                claude_md.write_text(
                    f"# {project_name}\n\n"
                    "SciTeX Cloud project. The `scitex` MCP server is connected.\n\n"
                    "## Usage\n\n"
                    "```python\n"
                    "import scitex as stx\n\n"
                    "@stx.session\n"
                    "def main(plt=stx.INJECTED, logger=stx.INJECTED):\n"
                    '    stx.io.save(data, "results.csv")\n'
                    "    return 0\n"
                    "```\n\n"
                    "## MCP Tools\n\n"
                    "Run `/mcp` in Claude Code to see available tools.\n"
                    "Run `/skills` to see SciTeX Cloud capabilities.\n"
                )

        logger.info("Created .claude/ config at %s", claude_dir)
        return True

    except Exception:
        logger.exception("Failed to create .claude/ config at %s", user_data_dir)
        return False


# EOF
