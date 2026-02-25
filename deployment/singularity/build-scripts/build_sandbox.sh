#!/bin/bash
# File: ./deployment/singularity/build-scripts/build_sandbox.sh
# ============================================
# Sandbox build: def → sandbox (always)
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects all variables and functions from common.sh.
#
# Usage: ./build.sh --sandbox [--force]
#
# Flow: def → sandbox (the only build path)
# SIF is only produced when explicitly requested (./build.sh without --sandbox)

run_sandbox_build() {
    local force="$1"

    local sandbox_dir="$SCRIPT_DIR/current-sandbox"

    # ----------------------------------------
    # Check if sandbox already exists
    # ----------------------------------------
    if [ -d "$sandbox_dir" ]; then
        if [ "$force" = "true" ]; then
            echo -e "${YELLOW}Sandbox already exists -- removing (--force passed): $sandbox_dir${NC}"
            rm -rf "$sandbox_dir"
        else
            echo -e "${YELLOW}Sandbox already exists: $sandbox_dir${NC}"
            echo -e ""
            echo -e "Use ${CYAN}--force${NC} to rebuild it:"
            echo -e "  ./build.sh --sandbox --force"
            echo -e ""
            _print_sandbox_usage "$sandbox_dir"
            exit 0
        fi
    fi

    # ----------------------------------------
    # Validate: def + base SIF required
    # ----------------------------------------
    if [ ! -f "$FINAL_DEF" ]; then
        echo -e "${RED}Error: Definition file not found: $FINAL_DEF${NC}"
        exit 1
    fi

    if [ ! -f "$BASE_SIF" ]; then
        echo -e "${RED}Error: Base SIF not found: $(basename "$BASE_SIF")${NC}"
        echo -e ""
        echo -e "The sandbox requires the base image."
        echo -e "Build it first with:"
        echo -e "  ${CYAN}./build.sh --base${NC}"
        exit 1
    fi

    # Inject correct base SIF path into a temp copy of the def
    local temp_def
    temp_def=$(mktemp "$SCRIPT_DIR/.scitex-sandbox-XXXXXX.def")
    # shellcheck disable=SC2064
    trap "rm -f '$temp_def'" EXIT

    sed \
        -e "s|^From:.*|From: ${BASE_SIF}|" \
        -e "s|SCITEX_VERSION_PLACEHOLDER|sandbox|" \
        -e "s|BASE_VERSION_PLACEHOLDER|v${BASE_VERSION}|" \
        -e "s|BUILD_DATE_PLACEHOLDER|$(date -u '+%Y-%m-%dT%H:%M:%SZ')|" \
        -e "s|BUILD_HOST_PLACEHOLDER|$(hostname)|" \
        -e "s|BUILD_MODE_PLACEHOLDER|sandbox|" \
        "$FINAL_DEF" >"$temp_def"

    local build_label
    build_label="def (${FINAL_DEF##*/} + $(basename "$BASE_SIF"))"

    # ----------------------------------------
    # Build sandbox from def
    # ----------------------------------------
    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Building SciTeX Sandbox (def → sandbox)${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Source:     ${GREEN}${build_label}${NC}"
    echo -e "Sandbox:    ${GREEN}$sandbox_dir${NC}"
    echo -e "Build mode: ${GREEN}$BUILD_MODE${NC}"
    echo -e ""

    check_disk_space 8

    echo -e "${GREEN}Building sandbox (this may take a few minutes)...${NC}"
    echo -e ""

    local start_time end_time elapsed_minutes elapsed_seconds
    start_time=$(date +%s)

    # shellcheck disable=SC2086  # FAKEROOT_FLAG intentionally unquoted (may be empty)
    if $CONTAINER_CMD build --sandbox $FAKEROOT_FLAG "$sandbox_dir" "$temp_def"; then
        end_time=$(date +%s)
        elapsed_minutes=$(((end_time - start_time) / 60))
        elapsed_seconds=$(((end_time - start_time) % 60))

        echo -e ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}Sandbox created successfully!${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo -e ""

        echo -e "Sandbox:    ${GREEN}$sandbox_dir${NC}"
        echo -e "Build time: ${GREEN}${elapsed_minutes}m ${elapsed_seconds}s${NC}"
        echo -e ""

        _print_sandbox_usage "$sandbox_dir"
    else
        echo -e ""
        echo -e "${RED}Sandbox build failed!${NC}"
        echo -e "Check the error messages above for details."
        exit 1
    fi
}

_print_sandbox_usage() {
    local sandbox_dir="$1"

    echo -e "${CYAN}-- Admin maintenance (writable shell) --${NC}"
    echo -e "To install packages or modify the container interactively:"
    echo -e ""
    echo -e "  $CONTAINER_CMD exec --writable --fakeroot \"${sandbox_dir}\" /bin/bash"
    echo -e ""
    echo -e "  make apptainer-sandbox-maintain  (shortcut)"
    echo -e ""
    echo -e "${CYAN}-- Convert sandbox to SIF (for distribution) --${NC}"
    echo -e "When done with modifications, convert to immutable SIF:"
    echo -e ""
    echo -e "  $CONTAINER_CMD build --fakeroot new.sif \"${sandbox_dir}\""
    echo -e ""
}

# EOF
