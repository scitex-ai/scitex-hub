#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-16
# Sync research-master template to a standalone git repository
# This allows the template to be version controlled independently
#
# Usage:
#   ./scripts/sync_research_template_to_git.sh [target_repo_path]
#
# Default target: ~/proj/examples/scitex_template_research
# Remote: https://github.com/ywatanabe1989/scitex-research-template

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_SRC="$PROJECT_ROOT/templates/research-master"
TARGET_REPO="${1:-$HOME/proj/examples/scitex_template_research}"
REMOTE_URL="https://github.com/ywatanabe1989/scitex-research-template"

echo "=== Syncing Research Template to Git Repository ==="
echo "Source: $TEMPLATE_SRC"
echo "Target: $TARGET_REPO"
echo ""

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_REPO" ]; then
    echo "Target repo not found. Cloning from remote..."
    mkdir -p "$(dirname "$TARGET_REPO")"
    git clone "$REMOTE_URL" "$TARGET_REPO" || {
        echo "Clone failed. Creating new repo..."
        mkdir -p "$TARGET_REPO"
        cd "$TARGET_REPO"
        git init
        echo "# SciTeX Research Template" > README.md
        echo "" >> README.md
        echo "Project template for SciTeX Cloud research projects." >> README.md
        git add README.md
        git commit -m "Initial commit"
        git remote add origin "$REMOTE_URL"
    }
elif [ ! -d "$TARGET_REPO/.git" ]; then
    echo "Directory exists but is not a git repo. Initializing..."
    cd "$TARGET_REPO"
    git init
    git remote add origin "$REMOTE_URL"
fi

# Sync files (excluding .git)
echo "Syncing files..."
rsync -av --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    "$TEMPLATE_SRC/" "$TARGET_REPO/"

# Show changes
cd "$TARGET_REPO"
echo ""
echo "=== Git Status ==="
git status --short

# Optionally commit
echo ""
read -p "Commit changes? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add -A
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "Sync from scitex-cloud ($TIMESTAMP)"
    echo ""
    echo "Changes committed. Push with: cd $TARGET_REPO && git push"
fi

echo ""
echo "=== Sync Complete ==="
