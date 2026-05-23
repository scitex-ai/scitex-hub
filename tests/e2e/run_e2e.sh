#!/bin/bash
# =============================================================================
# E2E Test Runner for SciTeX Cloud
#
# Usage:
#   ./run_e2e.sh              # Run against local dev (http://127.0.0.1:8000)
#   ./run_e2e.sh prod         # Run against production (https://scitex.ai)
#   ./run_e2e.sh prod-dev     # Run against prod dev (https://localhost:8443)
#   ./run_e2e.sh docker       # Run inside Docker container
#   ./run_e2e.sh <url>        # Run against custom URL
#
# Exit codes:
#   0 - All tests passed (safe to deploy)
#   1 - Tests failed (DO NOT deploy)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default configuration
DEFAULT_URL="http://127.0.0.1:8000"

# Parse arguments
case "${1:-local}" in
    local|dev)
        export SCITEX_BASE_URL="http://127.0.0.1:8000"
        ;;
    prod|production)
        export SCITEX_BASE_URL="https://scitex.ai"
        ;;
    prod-dev|staging)
        export SCITEX_BASE_URL="https://localhost:8443"
        ;;
    docker)
        # Run tests inside the Django container
        echo "Running E2E tests inside Docker container..."
        docker exec scitex-hub-prod-django-1 \
            python -m pytest /app/tests/e2e/ \
            -v --tb=short -x --timeout=60 \
            -o "addopts=" \
            "${@:2}"
        exit $?
        ;;
    http://*|https://*)
        export SCITEX_BASE_URL="$1"
        ;;
    *)
        echo "Unknown target: $1"
        echo "Usage: $0 [local|prod|prod-dev|docker|<url>]"
        exit 1
        ;;
esac

echo "=============================================="
echo "SciTeX E2E Tests"
echo "=============================================="
echo "Target: $SCITEX_BASE_URL"
echo "Time: $(date)"
echo "=============================================="

# Run tests
cd "$PROJECT_ROOT"

# Run with pytest, show failures immediately
# Override addopts to avoid Playwright browser args
python -m pytest tests/e2e/ \
    -v \
    --tb=short \
    -x \
    --timeout=60 \
    -o "addopts=" \
    "${@:2}"

EXIT_CODE=$?

echo ""
echo "=============================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
    echo "   Safe to deploy to: $SCITEX_BASE_URL"
else
    echo "❌ E2E tests FAILED!"
    echo "   DO NOT deploy until tests pass."
fi
echo "=============================================="

exit $EXIT_CODE
