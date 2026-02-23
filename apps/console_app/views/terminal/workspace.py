"""
Workspace Management
Handles user workspace setup and directory initialization
"""

import logging
from pathlib import Path

from .dotfiles import create_dotfiles_repo, create_dotfiles_symlinks

logger = logging.getLogger(__name__)


async def ensure_workspace(user_data_dir: Path, username: str, project_slug: str):
    """Ensure user workspace exists with proper structure"""
    import asyncio

    def setup():
        # Create directory structure
        user_data_dir.mkdir(parents=True, exist_ok=True)
        (user_data_dir / "proj").mkdir(exist_ok=True)
        (user_data_dir / ".singularity").mkdir(exist_ok=True)

        project_dir = user_data_dir / "proj" / project_slug
        project_dir.mkdir(exist_ok=True)

        # Create ~/proj/dotfiles as git repo (visible in project list)
        dotfiles_dir = user_data_dir / "proj" / "dotfiles"
        if not dotfiles_dir.exists():
            dotfiles_dir.mkdir()
            create_dotfiles_repo(dotfiles_dir, username)
            create_dotfiles_symlinks(user_data_dir, dotfiles_dir)
            logger.info(f"Created ~/proj/dotfiles git repo for {username}")

        # Patch existing bashrc with AI CLI tools section if missing
        _patch_bashrc_ai_tools(dotfiles_dir)

        logger.info(f"Workspace ready: {user_data_dir}")

    await asyncio.to_thread(setup)


def _patch_bashrc_ai_tools(dotfiles_dir: Path):
    """Ensure bashrc matches canonical template. Regenerates if corrupted."""
    bashrc = dotfiles_dir / "bashrc"
    if not bashrc.exists():
        return

    content = bashrc.read_text()

    # Detect corruption: orphaned done/fi, duplicate blocks, missing sections
    is_corrupted = (
        "\n    done\n" in content  # orphaned loop terminator
        or content.count("agents sync") > 1  # duplicate blocks
        or ".scitex-dev-installed" in content  # old dev block remnant
        or "# Show scitex version" in content  # old MOTD remnant
    )

    # Check required sections exist
    has_all_sections = all(
        marker in content
        for marker in [
            "tmux set -g mouse off",
            ".ai-cli-installed",
            "agents sync",
            "# Aliases",
        ]
    )

    if is_corrupted or not has_all_sections:
        # Extract username from PS1 prompt line
        username = "visitor"
        for line in content.splitlines():
            if "@scitex" in line and "PS1=" in line:
                import re

                m = re.search(r"\\](\S+?)@scitex", line)
                if m:
                    username = m.group(1)
                break

        # Regenerate from canonical template
        create_dotfiles_repo(dotfiles_dir, username)
        logger.info(f"Regenerated bashrc for {username} (was corrupted/outdated)")


# EOF
