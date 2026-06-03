#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-17 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/regenerate_gallery.sh
#
# Regenerates the plot gallery with correct axis metadata for alignment features.
# Gallery is stored in static/shared/images/gallery/ as single source of truth.
#
# This script should be run after any changes to:
# - scitex.plt.gallery plot functions
# - scitex.io.save metadata collection
# - scitex.plt.utils._crop cropping logic
#
# Usage:
#   ./scripts/maintenance/regenerate_gallery.sh
#   make regenerate-gallery  (via Makefile)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if docker is running
if ! docker ps &>/dev/null; then
    echo_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if the django container is running
CONTAINER_NAME="scitex-hub-dev-django-1"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo_error "Container ${CONTAINER_NAME} is not running."
    echo_info "Start the development environment with: make env=dev start"
    exit 1
fi

# Gallery output directory (single source of truth)
STATIC_GALLERY="${PROJECT_ROOT}/static/shared/images/gallery"
CONTAINER_STATIC_GALLERY="/app/static/shared/images/gallery"

# Legacy template gallery (to be removed)
CONTAINER_TEMPLATE_GALLERY="/app/templates/research-master/scitex/vis/gallery"

echo_info "Regenerating plot gallery..."
echo_info "Static gallery: ${STATIC_GALLERY}"

# Remove legacy template gallery if it exists
echo_info "Removing legacy template gallery (if exists)..."
docker exec "${CONTAINER_NAME}" bash -c "rm -rf '${CONTAINER_TEMPLATE_GALLERY}' 2>/dev/null || true"

# Clean existing static gallery
echo_info "Cleaning existing static gallery..."
docker exec "${CONTAINER_NAME}" bash -c "rm -rf '${CONTAINER_STATIC_GALLERY}'/* 2>/dev/null || true"

# Ensure directory exists
docker exec "${CONTAINER_NAME}" bash -c "mkdir -p '${CONTAINER_STATIC_GALLERY}'"

# Generate gallery using a Python script file (not heredoc) for proper path resolution
echo_info "Generating gallery plots with metadata..."
docker exec "${CONTAINER_NAME}" python3 /app/scripts/maintenance/_regenerate_gallery_worker.py

if [ $? -ne 0 ]; then
    echo_error "Gallery generation failed"
    exit 1
fi

# Verify gallery has JSON files with different axes_bbox_px
echo_info "Verifying axes metadata..."
docker exec "${CONTAINER_NAME}" python3 << 'PYEOF'
import json
import os

base = '/app/static/shared/images/gallery'

# Collect axes_bbox_px values
bbox_values = {}
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith('.json'):
            path = os.path.join(root, f)
            with open(path) as fh:
                d = json.load(fh)
                bbox = d.get('axes_bbox_px')
                if bbox:
                    key = f"{bbox.get('x0')},{bbox.get('y0')}"
                    rel = os.path.relpath(path, base)
                    if key not in bbox_values:
                        bbox_values[key] = []
                    bbox_values[key].append(rel)

# Check if we have different values
unique_x0_values = set(k.split(',')[0] for k in bbox_values.keys())
print(f"Found {len(unique_x0_values)} unique x0 values across gallery plots")

if len(unique_x0_values) > 1:
    print("SUCCESS: Gallery has varied axes positions for alignment")
else:
    print("WARNING: All plots have same axes position - alignment may not work correctly")
PYEOF

echo_info "Gallery regeneration complete!"
echo_info "Gallery location: ${STATIC_GALLERY}"
echo_info "To test alignment: navigate to /vis/ and use Alt+Ctrl+A on multiple plots"
