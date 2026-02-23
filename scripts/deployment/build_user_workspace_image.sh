#!/bin/bash
# Timestamp: "2025-11-14 17:45:00 (ywatanabe)"
# File: ./scripts/deployment/build_user_workspace_image.sh
# ============================================
# Build User Workspace Container Image
# ============================================

set -e

# Configuration
IMAGE_NAME="scitex-cloud-shared-v0.1.0"
VERSION="1.0.0"
DOCKERFILE="deployment/docker/Dockerfile.user-workspace"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Building User Workspace Image${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Image: $IMAGE_NAME:$VERSION"
echo "Dockerfile: $DOCKERFILE"
echo ""

# Build image
echo -e "${BLUE}Building image...${NC}"
docker build \
    -t $IMAGE_NAME:$VERSION \
    -t $IMAGE_NAME:latest \
    -f $DOCKERFILE \
    .

echo ""
echo -e "${GREEN}✓ Image built successfully${NC}"
echo ""
echo "Available tags:"
echo "  - $IMAGE_NAME:$VERSION"
echo "  - $IMAGE_NAME:latest"
echo ""

# Show image size
SIZE=$(docker images $IMAGE_NAME:latest --format "{{.Size}}")
echo "Image size: $SIZE"
echo ""

# Test image
echo -e "${BLUE}Testing image...${NC}"
docker run --rm $IMAGE_NAME:latest python3 -c "import numpy, pandas, matplotlib; print('✓ Scientific packages OK')"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Build Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Usage:"
echo "  # Run interactively"
echo "  docker run -it --rm $IMAGE_NAME:latest"
echo ""
echo "  # Test with user data"
echo "  docker run -it --rm -v /path/to/user/data:/home/user $IMAGE_NAME:latest"
echo ""

# EOF
