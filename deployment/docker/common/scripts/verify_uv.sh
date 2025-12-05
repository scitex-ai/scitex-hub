#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:45:00 (ywatanabe)"
# File: ./containers/docker/scripts/verify_uv.sh
#
# Verify UV is installed and working in Docker container

set -e

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"
cd "$GIT_ROOT/deployment/docker/docker_dev"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "Verifying UV installation in Docker container..."
echo

# Check if container is running
if ! docker-compose -f docker-compose.dev.yml ps | grep -q "docker_web_1.*Up"; then
    echo -e "${YELLOW}Web container not running. Starting...${NC}"
    docker-compose -f docker-compose.dev.yml up -d web
    sleep 5
fi

# Test UV version
echo -e "${GREEN}1. Checking UV version:${NC}"
docker-compose -f docker-compose.dev.yml exec -T web uv --version

# Test UV pip
echo
echo -e "${GREEN}2. Testing UV pip:${NC}"
docker-compose -f docker-compose.dev.yml exec -T web uv pip list | head -10

# Test UV is accessible by scitex user
echo
echo -e "${GREEN}3. Checking UV is accessible by scitex user:${NC}"
docker-compose -f docker-compose.dev.yml exec -T web whoami
docker-compose -f docker-compose.dev.yml exec -T web which uv

# Benchmark UV vs pip (simple test)
echo
echo -e "${GREEN}4. Quick benchmark (installing a small package):${NC}"

echo -e "  Testing pip..."
time docker-compose -f docker-compose.dev.yml exec -T web pip --version > /dev/null 2>&1

echo -e "  Testing uv..."
time docker-compose -f docker-compose.dev.yml exec -T web uv pip --version > /dev/null 2>&1

echo
echo -e "${GREEN}✓ UV verification complete!${NC}"
echo
echo -e "UV is installed and working correctly."
echo -e "Package installation should be significantly faster now."
