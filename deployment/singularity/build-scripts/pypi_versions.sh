#!/bin/bash
# File: ./deployment/singularity/build/pypi_versions.sh
# ============================================
# Fetch latest PyPI versions for cache-busting
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects: ECOSYSTEM_PKGS, GREEN, CYAN, NC (from common.sh)
# Sets:    PYPI_VERSIONS, SCITEX_VER

fetch_pypi_versions() {
    echo -e "${CYAN}Checking latest PyPI versions...${NC}"
    PYPI_VERSIONS=""
    local pkg ver
    for pkg in $ECOSYSTEM_PKGS; do
        ver=$(curl -s --max-time 5 "https://pypi.org/pypi/$pkg/json" 2>/dev/null |
            python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])" 2>/dev/null ||
            echo "unknown")
        PYPI_VERSIONS="${PYPI_VERSIONS}${pkg}==${ver} "
        echo -e "  ${pkg}: ${GREEN}${ver}${NC}"
    done
    PYPI_VERSIONS=$(echo "$PYPI_VERSIONS" | xargs)
}

# Extract scitex version from PYPI_VERSIONS string.
# Falls back to datestamp if unavailable.
resolve_scitex_version() {
    # shellcheck disable=SC2034  # SCITEX_VER is used by sourcing scripts
    SCITEX_VER=$(echo "$PYPI_VERSIONS" | grep -oP 'scitex==\K[^ ]+' || echo "")
    if [ -z "$SCITEX_VER" ] || [ "$SCITEX_VER" = "unknown" ]; then
        echo -e "${YELLOW}Warning: Could not determine scitex version from PyPI, using timestamp${NC}"
        SCITEX_VER="$(date +%Y%m%d)"
    fi
}

# EOF
