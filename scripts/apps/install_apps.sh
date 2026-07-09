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
    # Computed up front (not after the clone block) so the pip-fallback
    # below always probes the CURRENT app's package name. Previously this
    # was assigned after the clone attempt, so when clone failed for an
    # app it would reuse whatever $PKG_NAME the PREVIOUS loop iteration
    # had left behind — silently symlinking the sibling dir to a
    # different, unrelated installed package (observed: a private-repo
    # app's clone failed and the fallback matched the prior public app's
    # package instead, since find_spec() for that stale name still
    # resolved). Once wrong, the symlink resolves as a valid directory,
    # so `[[ ! -d "$SIBLING_DIR" ]]` never retries the clone on later
    # runs either — the bad state is sticky across restarts.
    PKG_NAME="${NAME//-/_}"

    echo ""
    echo "--- $NAME ---"

    # Resolve source directory
    if [[ "$FORCE_CLONE" == true ]] || [[ ! -d "$SIBLING_DIR" ]]; then
        if [[ -d "$SIBLING_DIR" ]] && [[ "$FORCE_CLONE" == true ]]; then
            echo "Sibling exists but --clone forced; skipping clone, using existing"
        else
            echo "Cloning $GIT_URL (ref: $GIT_REF) -> $SIBLING_DIR"
            if ! git clone --depth 1 --branch "$GIT_REF" "$GIT_URL" "$SIBLING_DIR" 2>&1; then
                echo "WARNING: Clone failed for $NAME — checking pip-installed package..."
                # Fall back to pip-installed package location
                PIP_STATIC=$(python3 -c "import importlib.util; spec = importlib.util.find_spec('${PKG_NAME}'); print(spec.submodule_search_locations[0] if spec else '')" 2>/dev/null || echo "")
                if [[ -n "$PIP_STATIC" ]] && [[ -d "$PIP_STATIC" ]]; then
                    echo "Found pip-installed $NAME at $PIP_STATIC — symlinking"
                    ln -sf "$(dirname "$(dirname "$PIP_STATIC")")" "$SIBLING_DIR"
                else
                    echo "WARNING: $NAME not available via git or pip — Vite bridge will be incomplete"
                fi
            fi
        fi
    else
        echo "Using existing sibling: $SIBLING_DIR"
    fi

    # Validate manifest exists
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

    # Run npm install for any package.json found (root or nested frontend dirs)
    while IFS= read -r pkg_json; do
        pkg_dir="$(dirname "$pkg_json")"
        echo "Running: npm install in $pkg_dir"
        (cd "$pkg_dir" && npm install --silent 2>/dev/null) || true
    done < <(find "$SIBLING_DIR" -maxdepth 5 -name "package.json" -not -path "*/node_modules/*" 2>/dev/null)

    echo "$NAME: OK"
done

echo ""
echo "All apps installed. Vite can now resolve bridge entries."
