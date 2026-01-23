#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-18 15:22:09 (ywatanabe)"
# File: ./scripts/mnist/main.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

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

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PATH="$0.log"
touch "$LOG_PATH"

cleanup() {
    rm -rf ./data/*
    rm -rf ./scripts/mnist/*_out
}

main() {
    ./scripts/mnist/01_download.py && \
    ./scripts/mnist/02_plot_digits.py && \
    ./scripts/mnist/03_plot_umap_space.py && \
    ./scripts/mnist/04_clf_svm.py && \
    ./scripts/mnist/05_plot_conf_mat.py
}

cleanup
main "$@" 2>&1 | tee "$LOG_PATH"

# EOF