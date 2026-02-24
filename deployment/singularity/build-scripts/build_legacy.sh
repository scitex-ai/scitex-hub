#!/bin/bash
# File: ./deployment/singularity/build/build_legacy.sh
# ============================================
# Legacy monolithic build (migration path)
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects all variables and functions from common.sh, hash_check.sh,
# pypi_versions.sh.

run_legacy_build() {
    local force="$1"

    if [ ! -f "$LEGACY_DEF" ]; then
        echo -e "${RED}Error: Legacy definition file not found: $LEGACY_DEF${NC}"
        exit 1
    fi

    # Fetch PyPI versions for cache-busting
    fetch_pypi_versions

    local current_hash
    current_hash=$(compute_hash "$LEGACY_DEF" "$PYPI_VERSIONS")

    if ! needs_rebuild "$force" "$LEGACY_SIF" "$LEGACY_HASH_FILE" "$current_hash" "Legacy"; then
        exit 0
    fi

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Building SciTeX Container (Legacy Monolithic)${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Definition: ${GREEN}$LEGACY_DEF${NC}"
    echo -e "Build mode: ${GREEN}$BUILD_MODE${NC}"

    backup_sif "$LEGACY_SIF"
    check_disk_space 6

    echo -e ""
    echo -e "${GREEN}Starting legacy build...${NC}"
    echo -e "This may take 15-30 minutes (downloads npm + Python packages)."
    echo -e ""

    local start_time end_time build_minutes build_seconds
    start_time=$(date +%s)

    # shellcheck disable=SC2086  # FAKEROOT_FLAG intentionally unquoted (may be empty)
    if $CONTAINER_CMD build --force $FAKEROOT_FLAG "$LEGACY_SIF" "$LEGACY_DEF"; then
        end_time=$(date +%s)
        build_minutes=$(((end_time - start_time) / 60))
        build_seconds=$(((end_time - start_time) % 60))

        save_hash "$LEGACY_HASH_FILE" "$current_hash"

        echo -e ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}Legacy build completed in ${build_minutes}m ${build_seconds}s${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo -e ""
        echo -e "Image: ${GREEN}$LEGACY_SIF${NC} ($(du -h "$LEGACY_SIF" | cut -f1))"
        echo -e ""

        echo -e "${GREEN}Running freeze...${NC}"
        if bash "$SCRIPT_DIR/freeze.sh" "$LEGACY_SIF"; then
            echo -e "${GREEN}Version lock files generated${NC}"
        else
            echo -e "${YELLOW}Freeze failed (non-critical)${NC}"
        fi
    else
        echo -e ""
        echo -e "${RED}Legacy build failed!${NC}"
        echo -e "Check the error messages above for details."
        exit 1
    fi
}

# EOF
