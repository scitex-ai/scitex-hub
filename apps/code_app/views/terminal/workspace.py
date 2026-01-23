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

        logger.info(f"Workspace ready: {user_data_dir}")

    await asyncio.to_thread(setup)


# EOF
