#!/bin/bash
# Color definitions for consistent terminal output

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ $*${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $*${NC}"
}

log_error() {
    echo -e "${RED}✗ $*${NC}" >&2
}
