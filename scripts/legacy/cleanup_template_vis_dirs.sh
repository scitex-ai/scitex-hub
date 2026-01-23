#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-16
# Remove noisy vis directories from research-master template

set -e

TEMPLATE_VIS_DIR="templates/research-master/scitex/vis"
DIRS_TO_REMOVE=("metadata" "panels" "pinned" "previews")

echo "Removing noisy directories from $TEMPLATE_VIS_DIR..."

for dir in "${DIRS_TO_REMOVE[@]}"; do
    target="$TEMPLATE_VIS_DIR/$dir"
    if [ -d "$target" ]; then
        echo "  Removing: $target"
        rm -rf "$target"
    else
        echo "  Already removed: $target"
    fi
done

echo "Done. Current structure:"
ls -la "$TEMPLATE_VIS_DIR"
