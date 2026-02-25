#!/usr/bin/env bash
# Timestamp: "2026-02-25"
# File: deployment/host-setup/scripts/manage-containers.sh
# ============================================================
# Container Version Management for SciTeX Cloud
#
# Uses scitex-container CLI for all operations.
# Keeps last N versions (default: 5) for rollback safety.
#
# Usage:
#   ./manage-containers.sh status       # Show current state
#   ./manage-containers.sh list         # List all versions
#   ./manage-containers.sh switch X.Y.Z # Switch active version
#   ./manage-containers.sh rollback     # Revert to previous
#   ./manage-containers.sh cleanup      # Remove old versions (keep 5)
#   ./manage-containers.sh build        # Build new SIF from .def
#   ./manage-containers.sh deploy       # Deploy active to /opt/scitex
#   ./manage-containers.sh rotate       # cleanup + deploy (for cron)
#   ./manage-containers.sh verify       # Verify active SIF integrity
# ============================================================

set -euo pipefail

# Configuration
CONTAINERS_DIR="${SCITEX_CONTAINERS_DIR:-/opt/scitex/singularity}"
KEEP_VERSIONS="${SCITEX_KEEP_VERSIONS:-5}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[container]${NC} $*"; }
warn() { echo -e "${YELLOW}[container]${NC} $*"; }
err() { echo -e "${RED}[container]${NC} $*" >&2; }

# Check scitex-container is available
check_cli() {
    if ! command -v scitex-container &>/dev/null; then
        err "scitex-container CLI not found."
        err "Install: pip install -e /home/ywatanabe/proj/scitex-container"
        exit 1
    fi
}

cmd_status() {
    check_cli
    log "Container status:"
    scitex-container status -d "$CONTAINERS_DIR" 2>/dev/null || {
        warn "No containers directory at $CONTAINERS_DIR"
        warn "Run: sudo mkdir -p $CONTAINERS_DIR && sudo chown \$(whoami) $CONTAINERS_DIR"
    }
}

cmd_list() {
    check_cli
    scitex-container list -d "$CONTAINERS_DIR"
}

cmd_switch() {
    local version="${1:?Usage: manage-containers.sh switch VERSION}"
    check_cli
    log "Switching to version $version..."
    scitex-container switch "$version" -d "$CONTAINERS_DIR"
}

cmd_rollback() {
    check_cli
    log "Rolling back to previous version..."
    scitex-container rollback -d "$CONTAINERS_DIR"
}

cmd_cleanup() {
    check_cli
    log "Cleaning up old versions (keeping last $KEEP_VERSIONS)..."
    scitex-container cleanup --keep "$KEEP_VERSIONS" -d "$CONTAINERS_DIR"
}

cmd_build() {
    local def_name="${1:-scitex-final}"
    check_cli
    log "Building SIF from $def_name..."
    scitex-container build "$def_name" -o "$CONTAINERS_DIR"
}

cmd_deploy() {
    check_cli
    log "Deploying active SIF to $CONTAINERS_DIR..."
    scitex-container deploy -d "$CONTAINERS_DIR" -t "$CONTAINERS_DIR"
}

cmd_verify() {
    check_cli
    log "Verifying active SIF..."
    scitex-container verify
}

cmd_rotate() {
    # Intended for cron: cleanup old + verify active
    check_cli
    log "Running rotation (cleanup + verify)..."
    cmd_cleanup
    cmd_verify
    log "Rotation complete."
}

cmd_help() {
    echo -e "${CYAN}Container Version Management${NC}"
    echo ""
    echo "Usage: $(basename "$0") <command> [args]"
    echo ""
    echo "Commands:"
    echo "  status            Show current container state"
    echo "  list              List all available versions"
    echo "  switch VERSION    Switch active container to VERSION"
    echo "  rollback          Revert to the previous version"
    echo "  cleanup           Remove old versions (keep $KEEP_VERSIONS)"
    echo "  build [NAME]      Build new SIF from .def file"
    echo "  deploy            Deploy active SIF to production path"
    echo "  verify            Verify active SIF integrity"
    echo "  rotate            Cleanup + verify (for cron jobs)"
    echo ""
    echo "Environment:"
    echo "  SCITEX_CONTAINERS_DIR  Container directory (default: /opt/scitex/singularity)"
    echo "  SCITEX_KEEP_VERSIONS   Versions to keep (default: 5)"
    echo ""
    echo "Cron example (weekly rotation):"
    echo "  0 3 * * 0 $SCRIPT_DIR/manage-containers.sh rotate >> /var/log/scitex-container-rotate.log 2>&1"
}

# Dispatch
case "${1:-help}" in
status) cmd_status ;;
list) cmd_list ;;
switch) cmd_switch "${2:-}" ;;
rollback) cmd_rollback ;;
cleanup) cmd_cleanup ;;
build) cmd_build "${2:-scitex-final}" ;;
deploy) cmd_deploy ;;
verify) cmd_verify ;;
rotate) cmd_rotate ;;
help | --help | -h) cmd_help ;;
*)
    err "Unknown command: $1"
    cmd_help
    exit 1
    ;;
esac

# EOF
