#!/bin/bash
# File: ./deployment/singularity/build-scripts/nightly_build.sh
# ============================================
# Nightly Apptainer build — resource-limited, non-disruptive
# ============================================
# Runs the base + final build at lowest priority so production
# services (web, SLURM, Docker) are never starved.
#
# Usage:
#   ./nightly_build.sh                 # Build if .def changed
#   ./nightly_build.sh --force         # Rebuild even if unchanged
#   ./nightly_build.sh --update-only   # Incremental pip install only
#   ./nightly_build.sh --help
#
# Cron example (2 AM daily, 1 CPU core max):
#   0 2 * * * /home/ywatanabe/proj/scitex-hub/deployment/singularity/build-scripts/nightly_build.sh >> /var/log/scitex-nightly-build.log 2>&1
#
# Resource limits:
#   - nice -n 19:     lowest CPU scheduling priority
#   - ionice -c 3:    idle I/O class (only uses I/O when nothing else needs it)
#   - OMP/MKL threads capped to 2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

LOG_DIR="$PARENT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/nightly-build-$(date +%Y%m%d-%H%M%S).log"

# ============================================
# Parse arguments
# ============================================
FORCE=false
UPDATE_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --force)
        FORCE=true
        shift
        ;;
    --update-only)
        UPDATE_ONLY=true
        shift
        ;;
    --help | -h)
        echo "Usage: $(basename "$0") [--force] [--update-only]"
        echo ""
        echo "Resource-limited Apptainer build for nightly cron."
        echo ""
        echo "Options:"
        echo "  --force         Rebuild even if .def hasn't changed"
        echo "  --update-only   Only run incremental pip install (skip .def build)"
        echo "  -h, --help      Show this help"
        echo ""
        echo "Resource limits applied:"
        echo "  nice -n 19      Lowest CPU priority"
        echo "  ionice -c 3     Idle I/O class"
        echo "  OMP_NUM_THREADS=2"
        echo ""
        echo "Cron example:"
        echo "  0 2 * * * $(realpath "$0") >> /var/log/scitex-nightly-build.log 2>&1"
        exit 0
        ;;
    *)
        echo "Unknown option: $1" >&2
        exit 1
        ;;
    esac
done

# ============================================
# Resource limiting wrapper
# ============================================
limited() {
    # Run command with hard resource caps + lowest priority.
    # systemd-run --scope enforces cgroup limits (CPU 80%, memory 80%)
    # so system services (sshd, kill) always have headroom.
    # Falls back to nice/ionice if systemd-run is unavailable.
    local cmd=(nice -n 19 ionice -c 3 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 "$@")
    if command -v systemd-run &>/dev/null; then
        systemd-run --scope --quiet \
            -p CPUQuota=80% \
            -p MemoryMax=80% \
            "${cmd[@]}"
    else
        "${cmd[@]}"
    fi
}

# ============================================
# Logging
# ============================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Nightly build started ==="
log "Host: $(hostname)"
log "Log: $LOG_FILE"

# ============================================
# Check if .def changed (skip if unchanged)
# ============================================
if [ "$UPDATE_ONLY" = true ]; then
    log "Mode: incremental update only (--update-only)"
elif [ "$FORCE" = true ]; then
    log "Mode: forced full rebuild (--force)"
else
    # Compare .def hash
    CURRENT_HASH=$(sha256sum "$BASE_DEF" 2>/dev/null | cut -d' ' -f1)
    STORED_HASH=""
    if [ -f "$BASE_HASH_FILE" ]; then
        STORED_HASH=$(cat "$BASE_HASH_FILE")
    fi

    if [ "$CURRENT_HASH" = "$STORED_HASH" ]; then
        log "Base .def unchanged (hash: ${CURRENT_HASH:0:12}...) — skipping base build"
        # Still do incremental update
        UPDATE_ONLY=true
    else
        log "Base .def changed — will rebuild"
        log "  Old hash: ${STORED_HASH:0:12}..."
        log "  New hash: ${CURRENT_HASH:0:12}..."
    fi
fi

# ============================================
# Full base build (if needed)
# ============================================
if [ "$UPDATE_ONLY" = false ]; then
    log "Starting base build: $BASE_DEF -> $BASE_SIF"
    log "Resource limits: nice -n 19, ionice -c 3, 2 threads"

    BUILD_START=$(date +%s)

    if limited apptainer build --force --fakeroot "$BASE_SIF" "$BASE_DEF" >>"$LOG_FILE" 2>&1; then
        BUILD_END=$(date +%s)
        BUILD_ELAPSED=$((BUILD_END - BUILD_START))
        log "Base build complete (${BUILD_ELAPSED}s)"

        # Store hash
        sha256sum "$BASE_DEF" | cut -d' ' -f1 >"$BASE_HASH_FILE"
    else
        BUILD_END=$(date +%s)
        BUILD_ELAPSED=$((BUILD_END - BUILD_START))
        log "ERROR: Base build failed after ${BUILD_ELAPSED}s"
        exit 1
    fi
fi

# ============================================
# Incremental sandbox update
# ============================================
log "Starting incremental sandbox update..."

if [ -x "$SCRIPT_DIR/update_sandbox.sh" ]; then
    if limited "$SCRIPT_DIR/update_sandbox.sh" >>"$LOG_FILE" 2>&1; then
        log "Sandbox update complete"
    else
        log "WARNING: Sandbox update had failures (see log)"
    fi
else
    log "SKIP: update_sandbox.sh not found or not executable"
fi

# ============================================
# Cleanup old logs (keep 30 days)
# ============================================
find "$LOG_DIR" -name "nightly-build-*.log" -mtime +30 -delete 2>/dev/null || true

log "=== Nightly build finished ==="

# EOF
