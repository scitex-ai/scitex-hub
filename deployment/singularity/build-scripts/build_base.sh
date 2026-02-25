#!/bin/bash
# File: ./deployment/singularity/build/build_base.sh
# ============================================
# Base container build (Stage 1)
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects all variables and functions from common.sh, hash_check.sh.

run_base_build() {
    local force="$1"

    if [ ! -f "$BASE_DEF" ]; then
        echo -e "${RED}Error: Base definition file not found: $BASE_DEF${NC}"
        exit 1
    fi

    local current_hash
    current_hash=$(compute_hash "$BASE_DEF")

    if ! needs_rebuild "$force" "$BASE_SIF" "$BASE_HASH_FILE" "$current_hash" "Base (v${BASE_VERSION})"; then
        exit 0
    fi

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Building SciTeX Base Container (Stage 1)${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Definition: ${GREEN}$BASE_DEF${NC}"
    echo -e "Output:     ${GREEN}$(basename "$BASE_SIF")${NC}"
    echo -e "Build mode: ${GREEN}$BUILD_MODE${NC}"

    backup_sif "$BASE_SIF"
    check_disk_space 10

    echo -e ""
    echo -e "${GREEN}Starting base build (this may take 20-30 minutes)...${NC}"
    echo -e ""

    local start_time end_time build_minutes build_seconds
    start_time=$(date +%s)

    # Inject metadata into a temp copy of the def
    local temp_def
    temp_def=$(mktemp "$SCRIPT_DIR/.scitex-base-XXXXXX.def")
    trap 'rm -f "$temp_def"' EXIT
    sed \
        -e "s|BASE_VERSION_PLACEHOLDER|v${BASE_VERSION}|" \
        -e "s|BUILD_DATE_PLACEHOLDER|$(date -u '+%Y-%m-%dT%H:%M:%SZ')|" \
        -e "s|BUILD_HOST_PLACEHOLDER|$(hostname)|" \
        "$BASE_DEF" >"$temp_def"

    # shellcheck disable=SC2086  # FAKEROOT_FLAG intentionally unquoted (may be empty)
    if $CONTAINER_CMD build --force $FAKEROOT_FLAG "$BASE_SIF" "$temp_def"; then
        end_time=$(date +%s)
        build_minutes=$(((end_time - start_time) / 60))
        build_seconds=$(((end_time - start_time) % 60))

        save_hash "$BASE_HASH_FILE" "$current_hash"

        echo -e ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}Base build completed successfully!${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo -e ""
        echo -e "Image file: ${GREEN}$(basename "$BASE_SIF")${NC}"
        echo -e "Image size: ${GREEN}$(du -h "$BASE_SIF" | cut -f1)${NC}"
        echo -e "Build time: ${GREEN}${build_minutes}m ${build_seconds}s${NC}"
        echo -e "Def hash:   ${GREEN}${current_hash:0:12}...${NC}"
        echo -e ""
        echo -e "${GREEN}Next step:${NC} Build final container:"
        echo -e "  ./build.sh"
        echo -e ""
    else
        echo -e ""
        echo -e "${RED}Base build failed!${NC}"
        echo -e "Check the error messages above for details."
        exit 1
    fi
}

# EOF
