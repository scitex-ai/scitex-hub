#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-16
# Update research-master template
# Run with: sudo ./scripts/update_research_template.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$PROJECT_ROOT/templates/research-master"
VIS_DIR="$TEMPLATE_DIR/scitex/vis"

echo "=== Updating Research Template ==="
echo "Template dir: $TEMPLATE_DIR"

# 1. Remove noisy directories from vis/
echo ""
echo "1. Removing noisy vis directories..."
DIRS_TO_REMOVE=("metadata" "panels" "pinned" "previews")
for dir in "${DIRS_TO_REMOVE[@]}"; do
    target="$VIS_DIR/$dir"
    if [ -d "$target" ]; then
        echo "   Removing: $dir/"
        rm -rf "$target"
    fi
done

# 2. Update vis/README.md
echo ""
echo "2. Updating vis/README.md..."
cat > "$VIS_DIR/README.md" << 'EOF'
# Visualization Directory

This directory contains all visualization-related files for your research project.

## Directory Structure

- `figures/` - Final publication-quality figures
- `gallery/` - Plot templates and examples by category
- `ai/` - AI-generated visualizations

## Supported File Types

The visualization workspace shows:
- Data files: `.csv`, `.tsv`, `.json`
- Images: `.png`, `.jpg`, `.jpeg`, `.svg`
- Plot archives: `.pltz.d`, `.figz.d`
- Documents: `.pdf`

## Getting Started

1. Create visualizations using the scripts in `/scripts/`
2. Save output images to `figures/`
3. Use the vis workspace (`/vis/`) to browse and manage your visualizations
4. Browse the `gallery/` for plot templates to get started quickly
EOF

# 3. Show final structure
echo ""
echo "3. Final vis/ structure:"
ls -la "$VIS_DIR"

echo ""
echo "=== Template Update Complete ==="
