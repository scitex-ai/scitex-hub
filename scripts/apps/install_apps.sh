#!/usr/bin/env bash
# Install workspace apps declared in .scitex-apps.json.
#
# Ensures app repos exist as siblings so Vite's bridge discovery
# can scan them. Clones from git_url if the sibling is absent.
#
# Usage:
#   bash scripts/apps/install_apps.sh          # auto: use sibling if present, clone if not
#   bash scripts/apps/install_apps.sh --clone   # force clone (for CI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PARENT_DIR="$(cd "$PROJECT_ROOT/.." && pwd)"
REGISTRY="$PROJECT_ROOT/.scitex-apps.json"

# In Docker, PARENT_DIR is / (not writable). Fall back to .apps/ inside project.
if [[ "$PARENT_DIR" == "/" ]] || [[ ! -w "$PARENT_DIR" ]]; then
    PARENT_DIR="$PROJECT_ROOT/.apps"
    mkdir -p "$PARENT_DIR"
fi

FORCE_CLONE=false
if [[ "${1:-}" == "--clone" ]]; then
    FORCE_CLONE=true
fi

if [[ ! -f "$REGISTRY" ]]; then
    echo "ERROR: $REGISTRY not found" >&2
    exit 1
fi

# Requires jq for JSON parsing
if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required but not installed" >&2
    exit 1
fi

APP_COUNT=$(jq '.apps | length' "$REGISTRY")
echo "Installing $APP_COUNT app(s) from $REGISTRY"

for i in $(seq 0 $((APP_COUNT - 1))); do
    NAME=$(jq -r ".apps[$i].name" "$REGISTRY")
    GIT_URL=$(jq -r ".apps[$i].git_url" "$REGISTRY")
    GIT_REF=$(jq -r ".apps[$i].git_ref // \"develop\"" "$REGISTRY")
    PIP_PKG=$(jq -r ".apps[$i].pip_package // \"\"" "$REGISTRY")

    SIBLING_DIR="$PARENT_DIR/$NAME"

    echo ""
    echo "--- $NAME ---"

    # Resolve source directory
    if [[ "$FORCE_CLONE" == true ]] || [[ ! -d "$SIBLING_DIR" ]]; then
        if [[ -d "$SIBLING_DIR" ]] && [[ "$FORCE_CLONE" == true ]]; then
            echo "Sibling exists but --clone forced; skipping clone, using existing"
        else
            echo "Cloning $GIT_URL (ref: $GIT_REF) -> $SIBLING_DIR"
            git clone --depth 1 --branch "$GIT_REF" "$GIT_URL" "$SIBLING_DIR"
        fi
    else
        echo "Using existing sibling: $SIBLING_DIR"
    fi

    # Validate manifest exists
    PKG_NAME="${NAME//-/_}"
    MANIFEST="$SIBLING_DIR/src/$PKG_NAME/_django/manifest.json"
    if [[ ! -f "$MANIFEST" ]]; then
        # Try repo root manifest
        MANIFEST="$SIBLING_DIR/manifest.json"
    fi
    if [[ -f "$MANIFEST" ]]; then
        echo "Manifest: $MANIFEST"
    else
        echo "WARNING: No manifest.json found for $NAME (no bridge)"
    fi

    # pip install
    if [[ -n "$PIP_PKG" ]]; then
        echo "Installing: pip install -e $SIBLING_DIR"
        pip install -e "$SIBLING_DIR" -q
    fi

    # Run npm install if the app has its own package.json with dependencies
    if [[ -f "$SIBLING_DIR/package.json" ]]; then
        echo "Running: npm install in $SIBLING_DIR"
        (cd "$SIBLING_DIR" && npm install --silent 2>/dev/null) || true
    fi

    echo "$NAME: OK"
done

echo ""
echo "All apps installed. Vite can now resolve bridge entries."
