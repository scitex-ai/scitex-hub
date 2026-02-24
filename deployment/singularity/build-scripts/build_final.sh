#!/bin/bash
# File: ./deployment/singularity/build/build_final.sh
# ============================================
# Final container build (Stage 2)
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects all variables and functions from common.sh, hash_check.sh,
# pypi_versions.sh, versions_json.sh.

run_final_build() {
    local force="$1"

    if [ ! -f "$FINAL_DEF" ]; then
        echo -e "${RED}Error: Final definition file not found: $FINAL_DEF${NC}"
        exit 1
    fi

    # Base SIF must exist
    if [ ! -f "$BASE_SIF" ]; then
        echo -e "${RED}Error: Base SIF not found: $(basename "$BASE_SIF")${NC}"
        echo -e ""
        echo -e "The final container requires the base image."
        echo -e "Build it first with:"
        echo -e "  ${CYAN}./build.sh --base${NC}"
        echo -e ""
        echo -e "Or check base version in: ${CYAN}$BASE_VERSION_FILE${NC}"
        exit 1
    fi

    echo -e "${CYAN}Base image: $(basename "$BASE_SIF") ($(du -h "$BASE_SIF" | cut -f1))${NC}"

    # Fetch PyPI versions and resolve scitex version
    fetch_pypi_versions
    resolve_scitex_version

    local final_sif="$SCRIPT_DIR/scitex-v${SCITEX_VER}.sif"
    echo -e "${CYAN}Target image: $(basename "$final_sif")${NC}"

    # Hash: def + PyPI versions
    local current_hash
    current_hash=$(compute_hash "$FINAL_DEF" "$PYPI_VERSIONS")

    if ! needs_rebuild "$force" "$final_sif" "$FINAL_HASH_FILE" "$current_hash" "Final (v${SCITEX_VER})"; then
        exit 0
    fi

    echo "$PYPI_VERSIONS" >"$VERSIONS_FILE"

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Building SciTeX Final Container (Stage 2)${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Base:       ${GREEN}$(basename "$BASE_SIF")${NC}"
    echo -e "Definition: ${GREEN}$FINAL_DEF${NC}"
    echo -e "Output:     ${GREEN}$(basename "$final_sif")${NC}"
    echo -e "Build mode: ${GREEN}$BUILD_MODE${NC}"

    backup_sif "$final_sif"
    check_disk_space 6

    # Inject correct base SIF path and metadata into a temp copy of the def
    local temp_def
    temp_def=$(mktemp "$SCRIPT_DIR/.scitex-final-XXXXXX.def")
    trap 'rm -f "$temp_def"' EXIT
    sed \
        -e "s|^From:.*|From: ${BASE_SIF}|" \
        -e "s|SCITEX_VERSION_PLACEHOLDER|${SCITEX_VER}|" \
        -e "s|BASE_VERSION_PLACEHOLDER|v${BASE_VERSION}|" \
        -e "s|BUILD_DATE_PLACEHOLDER|$(date -u '+%Y-%m-%dT%H:%M:%SZ')|" \
        -e "s|BUILD_HOST_PLACEHOLDER|$(hostname)|" \
        -e "s|BUILD_MODE_PLACEHOLDER|${BUILD_MODE}|" \
        "$FINAL_DEF" >"$temp_def"

    echo -e ""
    echo -e "${GREEN}Starting final build (this should take 2-5 minutes)...${NC}"
    echo -e ""

    local start_time end_time build_minutes build_seconds
    start_time=$(date +%s)

    # shellcheck disable=SC2086  # FAKEROOT_FLAG intentionally unquoted (may be empty)
    if $CONTAINER_CMD build --force $FAKEROOT_FLAG "$final_sif" "$temp_def"; then
        end_time=$(date +%s)
        build_minutes=$(((end_time - start_time) / 60))
        build_seconds=$(((end_time - start_time) % 60))

        save_hash "$FINAL_HASH_FILE" "$current_hash"

        # Symlink current.sif
        ln -sf "$(basename "$final_sif")" "$SCRIPT_DIR/current.sif"
        echo -e "${GREEN}Symlink updated: current.sif -> $(basename "$final_sif")${NC}"

        # Update versions.json
        local build_date sif_size
        build_date=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
        sif_size=$(du -h "$final_sif" | cut -f1)
        update_versions_json "$VERSIONS_JSON" "$SCITEX_VER" "$BASE_VERSION" \
            "$build_date" "${build_minutes}m ${build_seconds}s" \
            "$sif_size" "$current_hash" "$PYPI_VERSIONS"

        _print_final_success "$final_sif" "$sif_size" \
            "$build_minutes" "$build_seconds" "$current_hash"
    else
        echo -e ""
        echo -e "${RED}Build failed!${NC}"
        echo -e "Check the error messages above for details."
        exit 1
    fi
}

_print_final_success() {
    local final_sif="$1" sif_size="$2"
    local build_minutes="$3" build_seconds="$4" current_hash="$5"

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Image file: ${GREEN}$(basename "$final_sif")${NC}"
    echo -e "Image size: ${GREEN}${sif_size}${NC}"
    echo -e "Build time: ${GREEN}${build_minutes}m ${build_seconds}s${NC}"
    echo -e "Def hash:   ${GREEN}${current_hash:0:12}...${NC}"
    echo -e "Symlink:    ${GREEN}current.sif -> $(basename "$final_sif")${NC}"
    echo -e ""

    echo -e "${GREEN}Running freeze to capture installed versions...${NC}"
    if bash "$SCRIPT_DIR/freeze.sh" "$final_sif"; then
        echo -e "${GREEN}Version lock files generated${NC}"
    else
        echo -e "${YELLOW}Freeze failed (non-critical) -- run manually: ./freeze.sh${NC}"
    fi

    echo -e ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "  Test:    sudo ./test.sh"
    echo -e "  Restart: make env=dev restart"
    echo -e ""
}

# EOF
