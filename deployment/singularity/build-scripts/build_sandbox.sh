#!/bin/bash
# File: ./deployment/singularity/build-scripts/build_sandbox.sh
# ============================================
# Sandbox build: def → sandbox (timestamped + versioned)
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects all variables and functions from common.sh.
#
# Usage: ./build.sh --sandbox [--force]
#
# Flow: def → sandbox-YYYYMMDD_HHMMSS/ → current-sandbox symlink
# Keeps up to 5 sandboxes for rollback (configurable via SCITEX_KEEP_SANDBOXES)
# SIF is only produced when explicitly requested (./build.sh without --sandbox)

KEEP_SANDBOXES="${SCITEX_KEEP_SANDBOXES:-5}"

run_sandbox_build() {
    local force="$1"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local sandbox_dir="$SCRIPT_DIR/sandbox-${timestamp}"
    local symlink_path="$SCRIPT_DIR/current-sandbox"

    # ----------------------------------------
    # Check if --force: skip if active sandbox is recent (< 5 min)
    # ----------------------------------------
    if [ "$force" != "true" ] && [ -L "$symlink_path" ] && [ -d "$symlink_path" ]; then
        echo -e "${YELLOW}Active sandbox exists: $(readlink "$symlink_path")${NC}"
        echo -e ""
        echo -e "Use ${CYAN}--force${NC} to build a new version:"
        echo -e "  ./build.sh --sandbox --force"
        echo -e ""
        _print_sandbox_usage "$symlink_path"
        exit 0
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

        # Atomic symlink update
        _update_symlink "$sandbox_dir"

        echo -e ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}Sandbox created successfully!${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo -e ""

        echo -e "Sandbox:    ${GREEN}$sandbox_dir${NC}"
        echo -e "Symlink:    ${GREEN}current-sandbox -> $(basename "$sandbox_dir")${NC}"
        echo -e "Build time: ${GREEN}${elapsed_minutes}m ${elapsed_seconds}s${NC}"
        echo -e ""

        # Cleanup old sandboxes
        _cleanup_old_sandboxes

        _print_sandbox_usage "$symlink_path"
    else
        echo -e ""
        echo -e "${RED}Sandbox build failed!${NC}"
        echo -e "Check the error messages above for details."
        # Clean up failed build directory
        [ -d "$sandbox_dir" ] && rm -rf "$sandbox_dir"
        exit 1
    fi
}

_update_symlink() {
    local target_dir="$1"
    local target_name
    target_name=$(basename "$target_dir")
    local symlink_path="$SCRIPT_DIR/current-sandbox"
    local tmp_link="$SCRIPT_DIR/.current-sandbox.tmp.$$"

    ln -sfn "$target_name" "$tmp_link"
    mv -Tf "$tmp_link" "$symlink_path"
}

_cleanup_old_sandboxes() {
    local count=0
    local active_target=""

    if [ -L "$SCRIPT_DIR/current-sandbox" ]; then
        active_target=$(readlink "$SCRIPT_DIR/current-sandbox")
    fi

    # List sandbox-* dirs sorted by modification time (newest first)
    while IFS= read -r dir; do
        dir_name=$(basename "$dir")

        # Never remove active sandbox
        if [ "$dir_name" = "$active_target" ]; then
            continue
        fi

        count=$((count + 1))
        if [ "$count" -gt "$KEEP_SANDBOXES" ]; then
            echo -e "${YELLOW}Removing old sandbox: $dir_name${NC}"
            rm -rf "$dir"
        fi
    done < <(find "$SCRIPT_DIR" -maxdepth 1 -type d -name 'sandbox-*' -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)
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
    echo -e "${CYAN}-- Sandbox versioning --${NC}"
    echo -e "  make apptainer-sandbox-list      List all sandboxes"
    echo -e "  make apptainer-sandbox-rollback   Roll back to previous"
    echo -e "  make apptainer-sandbox-cleanup    Remove old sandboxes"
    echo -e ""
}

# EOF
