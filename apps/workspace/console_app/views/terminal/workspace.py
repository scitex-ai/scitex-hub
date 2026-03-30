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

        # Ensure scitex/downloads/ for paste/drop uploads
        (project_dir / "scitex" / "downloads").mkdir(parents=True, exist_ok=True)

        # Ensure directories are accessible from the host for SLURM bind mounts.
        # Docker creates these as root (UID 100019 on host via fakeroot),
        # but SLURM jobs run as the host user and need read+exec access.
        import os

        for d in [user_data_dir, user_data_dir / "proj", project_dir]:
            try:
                st = d.stat()
                if not (st.st_mode & 0o005):  # not world-readable+exec
                    os.chmod(d, st.st_mode | 0o755)
            except OSError:
                pass

        # Create ~/proj/dotfiles as git repo (visible in project list)
        dotfiles_dir = user_data_dir / "proj" / "dotfiles"
        if not dotfiles_dir.exists():
            dotfiles_dir.mkdir()
            create_dotfiles_repo(dotfiles_dir, username)
            create_dotfiles_symlinks(user_data_dir, dotfiles_dir)
            logger.info(f"Created ~/proj/dotfiles git repo for {username}")
        else:
            # Ensure dotfiles symlinks exist even if dotfiles dir was
            # created previously (e.g., interrupted setup, manual deletion).
            # Without these symlinks, bash cannot find .bashrc/.bash_profile
            # and the PS1 prompt is never set.
            _ensure_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        # Patch existing bashrc with AI CLI tools section if missing
        _patch_bashrc_ai_tools(dotfiles_dir)

        # Clean up legacy ~/proj/home -> .. symlink (replaced by dotfiles project)
        home_link = user_data_dir / "proj" / "home"
        if home_link.is_symlink():
            home_link.unlink()

        logger.info(f"Workspace ready: {user_data_dir}")

    await asyncio.to_thread(setup)


def _ensure_dotfiles_symlinks(user_data_dir: Path, dotfiles_dir: Path):
    """Verify critical dotfiles symlinks exist; recreate if missing.

    The .bashrc and .bash_profile symlinks are required for the PS1 prompt
    and shell initialization. If they are missing or broken, the terminal
    shows no prompt.
    """
    critical_symlinks = {
        ".bashrc": "proj/dotfiles/bashrc",
        ".bash_profile": "proj/dotfiles/bash_profile",
    }
    needs_repair = False
    for target_name, source_rel in critical_symlinks.items():
        target_path = user_data_dir / target_name
        source_file = user_data_dir / source_rel
        if not source_file.exists():
            # Dotfiles source files missing — need full regeneration
            needs_repair = True
            break
        if not target_path.exists() and not target_path.is_symlink():
            needs_repair = True
            break
        # Check if symlink target resolves correctly
        if target_path.is_symlink() and not target_path.resolve().exists():
            needs_repair = True
            break

    if needs_repair:
        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)
        logger.info(f"Repaired dotfiles symlinks in {user_data_dir}")


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
