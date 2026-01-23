#!/bin/bash
# Copy demo MEDIA files to container volume (for fresh deployments only)
# Code is included in Docker build - this script only handles media files
# that are stored outside the project repository.
#
# NOTE: Media volume is persistent - files survive rebuilds.
#       Only run this once for fresh deployments or when adding new demos.
#
# Added: 2026-01-16
# Simplified: 2026-01-22 - Removed code copying (now in build)

set -e

CONTAINER="scitex-cloud-nas-django-1"
NAS_HOME="/home/ywatanabe"

echo "Copying demo media files to container volume..."

# scitex-writer demo files (stored in NAS home, not in repo due to size)
if ! docker exec "$CONTAINER" ls /app/media/videos/scitex-writer-v2.2.0-demo.mp4 >/dev/null 2>&1; then
    echo "  Copying scitex-writer demo files..."
    for file in "$NAS_HOME"/scitex-writer-v2.2.0-demo*; do
        [ -f "$file" ] && docker cp "$file" "$CONTAINER:/app/media/videos/"
    done
fi

# scitex-automated-research demo files
if ! docker exec "$CONTAINER" ls /app/media/videos/scitex-automated-research-demo.mp4 >/dev/null 2>&1; then
    echo "  Copying scitex-automated-research demo files..."
    for file in "$NAS_HOME"/scitex-automated-research-demo*; do
        [ -f "$file" ] && docker cp "$file" "$CONTAINER:/app/media/videos/"
    done
fi

echo "Done! Media files are now in the persistent volume."
