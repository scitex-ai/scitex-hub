#!/bin/bash
# File: examples/scitex_hub/00_run_all.sh
# Run all scitex-hub examples

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== SciTeX Hub Examples ==="
echo

# Example 1: Show version and help
echo "--- Example 01: CLI Basics ---"
bash "$SCRIPT_DIR/01_cli_basics.sh"
echo

# Example 2: Environment configuration
echo "--- Example 02: Environment Config ---"
python "$SCRIPT_DIR/02_environment_config.py"
echo

# Example 3: Docker manager (dry run)
echo "--- Example 03: Docker Manager ---"
python "$SCRIPT_DIR/03_docker_manager.py"
echo

echo "=== All examples completed ==="
