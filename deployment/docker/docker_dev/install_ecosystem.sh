#!/bin/bash
# ============================================
# SciTeX Ecosystem Package Installer (Editable Mode)
# ============================================
# Shared helper for installing sibling packages mounted into Docker.
# Sourced by entrypoint.sh — expects GREEN, NC, echo_info to be defined.

# Mark all mounted repos as safe for git (prevents "dubious ownership" errors)
git config --global --add safe.directory '*' 2>/dev/null || true

# Generic editable install function
# Usage: try_editable_install <mount_path> <package_name> [extras]
#   mount_path:    e.g. /figrecipe
#   package_name:  e.g. figrecipe (used for pip show check)
#   extras:        e.g. [all] (optional, default: no extras)
try_editable_install() {
    local mount_path="$1"
    local pkg_name="$2"
    local extras="${3:-}"
    local install_spec="${mount_path}${extras}"

    if [ ! -d "$mount_path" ]; then
        echo -e "⚠️  WARNING: $mount_path not mounted, skipping..."
        return
    fi

    if [ ! -f "$mount_path/pyproject.toml" ] && [ ! -f "$mount_path/setup.py" ]; then
        echo -e "⚠️  WARNING: $mount_path exists but is not a valid Python package"
        return
    fi

    # For figrecipe: always reinstall to pick up new files
    if [ "$pkg_name" = "figrecipe" ]; then
        echo_info "Installing $pkg_name (editable mode)..."
        if ! uv pip install -e "$install_spec" --link-mode=copy 2>&1; then
            echo_warning "$pkg_name install failed (non-fatal)"
        fi
        return
    fi

    # For others: skip if already installed in editable mode from the mount
    if pip show "$pkg_name" 2>/dev/null | grep -q "Location:.*${pkg_name}"; then
        echo -e "${GREEN}✅ $pkg_name already installed in editable mode${NC}"
    else
        echo_info "Installing $pkg_name (editable mode)..."
        if ! uv pip install -e "$install_spec" --link-mode=copy 2>&1; then
            echo_warning "$pkg_name install failed (non-fatal)"
        fi
    fi
}

# Install scitex-core FIRST (many packages depend on it: scitex-db, scitex-python, etc.)
try_editable_install "/scitex-core" "scitex-core"

# Install scitex core dependencies BEFORE scitex[all] (scitex depends on these)
try_editable_install "/scitex-clew" "scitex-clew"
try_editable_install "/scitex-io" "scitex-io" "[all]"
try_editable_install "/scitex-stats" "scitex-stats" "[all]"
try_editable_install "/scitex-tunnel" "scitex-tunnel"
try_editable_install "/scitex-audio" "scitex-audio" "[all]"
try_editable_install "/scitex-scholar" "scitex-scholar"
try_editable_install "/scitex-notification" "scitex-notification"
try_editable_install "/scitex-db" "scitex-db"

# Install scitex[all] from local mount
# Use pip (not uv) for this step: uv's resolver fails to find private scitex-*
# packages on PyPI even when they're already installed locally. pip respects
# already-installed packages during dependency resolution.
if [ -d "/scitex-python" ]; then
    if [ -f "/scitex-python/pyproject.toml" ] || [ -f "/scitex-python/setup.py" ]; then
        echo_info "Installing scitex[all] (editable, using pip for local dep resolution)..."
        if ! pip install --no-build-isolation -e "/scitex-python[all]" 2>&1; then
            echo_warning "scitex[all] install failed - trying without extras..."
            if ! pip install --no-build-isolation -e "/scitex-python" 2>&1; then
                echo_warning "scitex install failed (non-fatal)"
            fi
        fi
        verify_scitex_package
    else
        echo -e "⚠️  WARNING: /scitex-python exists but is not a valid Python package"
        echo -e "   (missing pyproject.toml or setup.py at root)"
    fi
else
    echo -e "⚠️  WARNING: /scitex-python not mounted!"
fi

# Install scitex-ui (required: in INSTALLED_APPS, must be available before Django starts)
try_editable_install "/scitex-ui" "scitex-ui"

# Install scitex-app (required: core SDK for app paths, preferences, cloud integration)
try_editable_install "/scitex-app" "scitex-app"

# Install scitex-container (required: terminal broker needs scitex_container.apptainer)
try_editable_install "/scitex-container" "scitex-container"

# Install scitex-cloud itself in editable mode
if [ -f "/app/pyproject.toml" ]; then
    echo_info "Installing scitex-cloud (editable)..."
    uv pip install -e "/app" --link-mode=copy 2>&1 || true
fi

# Install ecosystem packages (skip on hot-reload — packages persist in container)
install_ecosystem_packages() {
    if [ -f "$MIGRATION_SENTINEL" ]; then
        echo_info "Hot-reload restart - skipping ecosystem package installations"
        return
    fi

    try_editable_install "/figrecipe" "figrecipe" "[all]"
    try_editable_install "/scitex-writer" "scitex-writer" "[all]"
    try_editable_install "/crossref-local" "crossref-local" "[all]"
    try_editable_install "/openalex-local" "openalex-local" "[all]"
    try_editable_install "/socialia" "socialia" "[all]"
    try_editable_install "/scitex-dev" "scitex-dev" "[all]"
    try_editable_install "/scitex-dataset" "scitex-dataset" "[all]"
    try_editable_install "/scitex-linter" "scitex-linter"
    try_editable_install "/scitex-scholar" "scitex-scholar" "[all]"
    try_editable_install "/scitex-container" "scitex-container"
    try_editable_install "/scitex-plt" "scitex-plt" "[all]"

    # Ensure pygments is available
    if ! python -c "import pygments" 2>/dev/null; then
        echo_info "Installing pygments..."
        pip install --no-cache-dir pygments >/dev/null 2>&1 || true
    fi
}
install_ecosystem_packages
