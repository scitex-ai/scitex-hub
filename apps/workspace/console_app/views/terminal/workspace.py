"""
Workspace Management
Handles user workspace setup and directory initialization
"""

import logging
import os
import stat
from pathlib import Path

from .dotfiles import create_dotfiles_repo, create_dotfiles_symlinks

logger = logging.getLogger(__name__)

# The floor every workspace directory is pinned to, EXPLICITLY.
#
# ``mkdir``/``makedirs`` cannot express this: their ``mode=`` argument is
# masked by the caller's umask. Measured 2026-08-22 on this interpreter,
# ``os.makedirs(mode=0o755)`` yields 0755 at umask 0022, 0750 at umask 0027 and
# 0700 at umask 0077, while ``os.chmod(0o755)`` yields 0755 at every one of
# them. A workspace whose permissions depend on the ambient umask of whichever
# process happened to spawn the terminal is the defect, not the symptom — so
# the mode is asserted after creation, by chmod, unconditionally.
WORKSPACE_DIR_MODE = 0o755


def ensure_workspace_sync(user_data_dir: Path, username: str, project_slug: str):
    """Ensure user workspace exists with proper structure (sync core).

    Called from the async spawn path via :func:`ensure_workspace` and
    directly (synchronously) by the visitor-pool reset pipeline, which
    recreates the home skeleton after wiping the entire visitor home
    root (``visitor_pool.workspace_manager``). Keep it the single
    source of truth for the home-directory layout.
    """
    # Create directory structure
    user_data_dir.mkdir(parents=True, exist_ok=True)
    (user_data_dir / "proj").mkdir(exist_ok=True)
    (user_data_dir / ".singularity").mkdir(exist_ok=True)

    project_dir = user_data_dir / "proj" / project_slug
    project_dir.mkdir(exist_ok=True)

    # Ensure scitex/downloads/ for paste/drop uploads
    (project_dir / "scitex" / "downloads").mkdir(parents=True, exist_ok=True)

    # Pin the mode of everything just created. Two reasons, and the second is
    # why this is unconditional now:
    #
    #  * SLURM bind mounts and host-side tooling read this tree as other
    #    identities and need read+exec.
    #  * The health check behind the site-wide "Server:" badge lists every
    #    directory under ``data/users`` and marks the WHOLE check unhealthy on
    #    a single PermissionError. Measured 2026-08-16: one visitor home at
    #    mode 0700 rendered "Server: partial" in the header for every visitor,
    #    anonymous ones included, for days, with nothing connecting the two.
    #
    # The previous form was `if not (st.st_mode & 0o005): chmod(... | 0o755)`.
    # That test is an OR over two bits, so mode 0701 — execute-for-other but
    # not read — satisfied it and was left un-widened, unlistable and silent.
    # Bits are only ever ADDED here: narrowing a directory as a side effect of
    # a repair is the mechanism this whole change is about.
    for d in [
        user_data_dir,
        user_data_dir / "proj",
        user_data_dir / ".singularity",
        project_dir,
    ]:
        try:
            current = stat.S_IMODE(d.stat().st_mode)
            if current & WORKSPACE_DIR_MODE != WORKSPACE_DIR_MODE:
                os.chmod(d, current | WORKSPACE_DIR_MODE)
        except OSError as exc:
            # Not fatal here — an ordinary terminal spawn must not be blocked
            # by a directory somebody else owns — but never silent either: the
            # consequence is a page that cannot read its own workspace and a
            # degraded site badge, and this used to be a bare `pass`.
            logger.error(
                f"Could not pin mode {WORKSPACE_DIR_MODE:04o} on {d} for "
                f"{username}: {exc}. If the app cannot list it, the workspace "
                f"is unreadable AND the site-wide health badge reports "
                f"degraded until it is fixed."
            )

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


async def ensure_workspace(user_data_dir: Path, username: str, project_slug: str):
    """Ensure user workspace exists with proper structure"""
    import asyncio

    await asyncio.to_thread(
        ensure_workspace_sync, user_data_dir, username, project_slug
    )


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
