"""
Dotfiles Management
Creates and manages user dotfiles repository with default configurations
"""

import logging
import os
import subprocess as sp
from pathlib import Path

logger = logging.getLogger(__name__)


def create_dotfiles_repo(dotfiles_dir: Path, username: str):
    """Create ~/.dotfiles as a git repository with default configs"""
    # bashrc
    (dotfiles_dir / "bashrc").write_text(f'''# SciTeX Cloud - bashrc
# Edit this file and run ./install.sh to apply changes

# Emacs-style editing
set -o emacs

# History settings
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoredups:erasedups

# Prompt: {username}@scitex:~/path $
PS1='\\[\\033[01;32m\\]{username}@scitex\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\] \\$ '

# Aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'

# Python
alias python=python3
alias pip=pip3

# Git
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

# Auto-activate .venv if present
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi
''')

    # bash_profile
    (dotfiles_dir / "bash_profile").write_text('''# SciTeX Cloud - bash_profile
# Sources bashrc for login shells

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
''')

    # vimrc
    (dotfiles_dir / "vimrc").write_text('''" SciTeX Cloud - vimrc
" Edit this file to customize vim

syntax on
set number
set relativenumber
set expandtab
set tabstop=4
set shiftwidth=4
set autoindent
set smartindent
set hlsearch
set incsearch
set ignorecase
set smartcase
set ruler
set showcmd
set wildmenu
set backspace=indent,eol,start

" Color scheme (if available)
silent! colorscheme desert
''')

    # gitconfig
    (dotfiles_dir / "gitconfig").write_text(f'''# SciTeX Cloud - gitconfig
[user]
    name = {username}
    email = {username}@scitex.cloud

[core]
    editor = vim
    autocrlf = input

[color]
    ui = auto

[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    lg = log --oneline --graph --decorate -10

[pull]
    rebase = false

[init]
    defaultBranch = main
''')

    # tmux.conf
    (dotfiles_dir / "tmux.conf").write_text('''# SciTeX Cloud - tmux.conf

# Use Ctrl-a as prefix (like screen)
# unbind C-b
# set -g prefix C-a
# bind C-a send-prefix

# Mouse support
set -g mouse on

# 256 colors
set -g default-terminal "xterm-256color"

# Start window numbering at 1
set -g base-index 1
setw -g pane-base-index 1

# Faster escape time
set -sg escape-time 10

# History limit
set -g history-limit 10000

# Status bar
set -g status-style bg=black,fg=white
set -g status-left '[#S] '
set -g status-right '%H:%M %d-%b'
''')

    # ipython config
    ipython_dir = dotfiles_dir / "ipython"
    ipython_dir.mkdir(exist_ok=True)
    (ipython_dir / "ipython_config.py").write_text('''# SciTeX Cloud - IPython configuration
c = get_config()

# Cleaner prompts
c.TerminalInteractiveShell.banner1 = ''
c.TerminalInteractiveShell.banner2 = ''
c.TerminalInteractiveShell.confirm_exit = False

# Auto-reload modules
c.InteractiveShellApp.extensions = ['autoreload']
c.InteractiveShellApp.exec_lines = ['%autoreload 2']
''')

    # install.sh
    (dotfiles_dir / "install.sh").write_text('''#!/bin/bash
# SciTeX Cloud - Dotfiles installer
# Run this after editing dotfiles to apply changes

DOTFILES_DIR="$HOME/proj/dotfiles"

echo "Installing dotfiles..."

# Create symlinks
ln -sf "$DOTFILES_DIR/bashrc" "$HOME/.bashrc"
ln -sf "$DOTFILES_DIR/bash_profile" "$HOME/.bash_profile"
ln -sf "$DOTFILES_DIR/vimrc" "$HOME/.vimrc"
ln -sf "$DOTFILES_DIR/gitconfig" "$HOME/.gitconfig"
ln -sf "$DOTFILES_DIR/tmux.conf" "$HOME/.tmux.conf"

# IPython
mkdir -p "$HOME/.ipython/profile_default"
ln -sf "$DOTFILES_DIR/ipython/ipython_config.py" "$HOME/.ipython/profile_default/ipython_config.py"

echo "Done! Restart your shell or run: source ~/.bashrc"
''')
    (dotfiles_dir / "install.sh").chmod(0o755)

    # README
    (dotfiles_dir / "README.md").write_text(f'''# {username}'s Dotfiles

Personal configuration files for SciTeX Cloud.

## Usage

Edit any file, then run:

```bash
./install.sh
source ~/.bashrc
```

## Files

| File | Description |
|------|-------------|
| `bashrc` | Shell configuration, aliases, prompt |
| `bash_profile` | Login shell (sources bashrc) |
| `vimrc` | Vim editor settings |
| `gitconfig` | Git configuration |
| `tmux.conf` | Tmux terminal multiplexer |
| `ipython/` | IPython configuration |

## Customization

Feel free to edit any file! Your changes are version controlled.

```bash
git add -A
git commit -m "Updated bashrc aliases"
```

## Sync to Local Machine

```bash
git clone <this-repo> ~/.dotfiles
cd ~/.dotfiles
./install.sh
```
''')

    # .gitignore
    (dotfiles_dir / ".gitignore").write_text('''# OS files
.DS_Store
Thumbs.db

# Backup files
*~
*.swp
*.bak
''')

    # Initialize git repo
    try:
        sp.run(["git", "init"], cwd=dotfiles_dir, capture_output=True)
        sp.run(["git", "add", "-A"], cwd=dotfiles_dir, capture_output=True)
        sp.run(
            ["git", "commit", "-m", "Initial dotfiles setup"],
            cwd=dotfiles_dir,
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": username,
                 "GIT_AUTHOR_EMAIL": f"{username}@scitex.cloud",
                 "GIT_COMMITTER_NAME": username,
                 "GIT_COMMITTER_EMAIL": f"{username}@scitex.cloud"}
        )
    except Exception as e:
        logger.warning(f"Git init failed (non-critical): {e}")


def create_dotfiles_symlinks(user_data_dir: Path, dotfiles_dir: Path):
    """Create symlinks from ~/ to ~/proj/dotfiles/"""
    symlinks = {
        ".bashrc": "bashrc",
        ".bash_profile": "bash_profile",
        ".vimrc": "vimrc",
        ".gitconfig": "gitconfig",
        ".tmux.conf": "tmux.conf",
    }

    for target, source in symlinks.items():
        target_path = user_data_dir / target
        source_path = dotfiles_dir / source

        # Remove existing file/symlink
        if target_path.exists() or target_path.is_symlink():
            target_path.unlink()

        # Create symlink (use relative path for portability)
        target_path.symlink_to(f"proj/dotfiles/{source}")

    # IPython config (nested)
    ipython_profile = user_data_dir / ".ipython" / "profile_default"
    ipython_profile.mkdir(parents=True, exist_ok=True)
    ipython_config = ipython_profile / "ipython_config.py"
    if ipython_config.exists() or ipython_config.is_symlink():
        ipython_config.unlink()
    ipython_config.symlink_to("../../proj/dotfiles/ipython/ipython_config.py")


# EOF
