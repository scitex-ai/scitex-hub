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
    """Add AI CLI tools auto-install block to existing bashrc if missing."""
    bashrc = dotfiles_dir / "bashrc"
    if not bashrc.exists():
        return

    content = bashrc.read_text()
    changed = False

    # Patch 1: AI CLI tools auto-install block
    if ".ai-cli-installed" not in content:
        ai_block = """
# AI CLI tools (npm global prefix + nvm)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export PATH="$HOME/.npm-global/bin:$PATH"

# Auto-install AI CLI tools on first login (one-time setup)
if ! command -v claude &>/dev/null && ! [ -f "$HOME/.ai-cli-installed" ]; then
    echo -e "\\033[0;36m[SciTeX] Installing AI CLI tools (one-time setup)...\\033[0m"
    if ! command -v node &>/dev/null; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm install 20 --lts 2>/dev/null
    fi
    if command -v npm &>/dev/null; then
        mkdir -p "$HOME/.npm-global"
        npm config set prefix "$HOME/.npm-global"
        npm install -g @anthropic-ai/claude-code @openai/codex @google/gemini-cli @agents-dev/cli 2>/dev/null
        touch "$HOME/.ai-cli-installed"
        echo -e "\\033[0;32m[SciTeX] AI CLI tools installed: claude, codex, gemini, agents\\033[0m"
    fi
fi
"""
        marker = "# Aliases"
        if marker in content:
            content = content.replace(marker, ai_block + marker)
        else:
            content += ai_block
        changed = True

    # Patch 2: agents sync block (pushes MCP config to all AI CLIs)
    if ".agents-synced" not in content:
        sync_block = """
# Sync MCP config to all AI tools on login
if command -v agents &>/dev/null && [ -d ".agents" ]; then
    agents sync --quiet 2>/dev/null
fi
"""
        # Insert after .ai-cli-installed block (after the closing fi)
        marker = "# Aliases"
        if marker in content:
            content = content.replace(marker, sync_block + marker)
        else:
            content += sync_block
        changed = True

    # Patch 3: Dev mode editable install from mounted repos
    if ".scitex-dev-installed" not in content:
        dev_block = """
# Dev mode: editable install from mounted repos (only in dev with bind mounts)
if [ ! -f /tmp/.scitex-dev-installed ] && [ -d /opt/dev/scitex-python ]; then
    echo -e "\\033[0;90m[SciTeX] Installing dev packages (editable)...\\033[0m"
    for repo in /opt/dev/*/; do
        if [ -f "$repo/pyproject.toml" ]; then
            pip install -e "$repo[all]" --quiet --no-deps 2>/dev/null || true
        fi
    done
    # Resolve all deps in one pass
    pip install -e "/opt/dev/scitex-python[all]" --quiet 2>/dev/null || true
    touch /tmp/.scitex-dev-installed
    echo -e "\\033[0;32m[SciTeX] Dev packages installed (editable)\\033[0m"
fi
"""
        marker = "# Aliases"
        if marker in content:
            content = content.replace(marker, dev_block + marker)
        else:
            content += dev_block
        changed = True

    # Patch 4: scitex version MOTD on login
    # Fix old format "scitex v${_V}" → "$_V" (was producing "scitex vscitex, version X.Y.Z")
    if 'echo -e "\\033[0;36m[SciTeX Cloud] scitex v' in content:
        content = content.replace(
            'echo -e "\\033[0;36m[SciTeX Cloud] scitex v${_V}\\033[0m"',
            'echo -e "\\033[0;36m[SciTeX Cloud] $_V\\033[0m"',
        )
        # Also fix the f-string variant from dotfiles.py
        content = content.replace(
            'echo -e "\\033[0;36m[SciTeX Cloud] scitex v$_V\\033[0m"',
            'echo -e "\\033[0;36m[SciTeX Cloud] $_V\\033[0m"',
        )
        changed = True
    elif "[SciTeX Cloud]" not in content:
        motd_block = """
# Show scitex version on login
if command -v scitex &>/dev/null; then
    _V=$(scitex --version 2>/dev/null | head -1)
    echo -e "\\033[0;36m[SciTeX Cloud] $_V\\033[0m"
    unset _V
fi
"""
        # Insert after PS1 line
        marker = "# AI CLI tools"
        if marker in content:
            content = content.replace(marker, motd_block + marker)
        else:
            marker = "# Aliases"
            if marker in content:
                content = content.replace(marker, motd_block + marker)
            else:
                content += motd_block
        changed = True

    if changed:
        bashrc.write_text(content)
        logger.info("Patched existing bashrc with AI CLI tools and agents sync")


# EOF
