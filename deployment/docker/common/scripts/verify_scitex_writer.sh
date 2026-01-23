#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-01 16:03:07 (ywatanabe)"
# File: ./containers/docker/scripts/verify_scitex_writer.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------
# containers/docker/scripts/verify_scitex_writer.sh

echo -e "=== Verifying scitex.writer dependencies ==="

check_cmd() {
    if command -v $1 &> /dev/null; then
        echo -e "✓ $1: $(command -v $1)"
    else
        echo -e "✗ $1: NOT FOUND"
        exit 1
    fi
}

# Essential tools
check_cmd pdflatex
check_cmd bibtex
check_cmd latexdiff
check_cmd yq
check_cmd jq

# Diagram tools
check_cmd convert # ImageMagick
check_cmd mmdc    # Mermaid CLI

# Python packages
python -c "import bibtexparser" && echo -e "✓ bibtexparser" || echo -e "✗ bibtexparser"

echo -e "=== All dependencies verified! ==="

# EOF
