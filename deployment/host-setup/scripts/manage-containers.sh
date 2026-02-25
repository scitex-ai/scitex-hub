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

cmd_sandbox_list() {
    check_cli
    scitex-container sandbox list -d "$CONTAINERS_DIR"
}

cmd_sandbox_switch() {
    local version="${1:?Usage: manage-containers.sh sandbox-switch VERSION}"
    check_cli
    log "Switching sandbox to $version..."
    scitex-container sandbox switch "$version" -d "$CONTAINERS_DIR"
}

cmd_sandbox_rollback() {
    check_cli
    log "Rolling back to previous sandbox..."
    scitex-container sandbox rollback -d "$CONTAINERS_DIR"
}

cmd_sandbox_cleanup() {
    check_cli
    log "Cleaning up old sandboxes (keeping last $KEEP_VERSIONS)..."
    scitex-container sandbox cleanup --keep "$KEEP_VERSIONS" -d "$CONTAINERS_DIR"
}

cmd_purge_sifs() {
    check_cli
    log "Removing all SIF files from $CONTAINERS_DIR..."
    scitex-container sandbox purge-sifs -d "$CONTAINERS_DIR"
}

cmd_rotate() {
    # Intended for cron: cleanup old sandboxes
    check_cli
    log "Running rotation (cleanup sandboxes)..."
    cmd_sandbox_cleanup
    log "Rotation complete."
}

cmd_help() {
    echo -e "${CYAN}Container Version Management${NC}"
    echo ""
    echo "Usage: $(basename "$0") <command> [args]"
    echo ""
    echo "Sandbox commands (primary):"
    echo "  sandbox-list         List versioned sandboxes"
    echo "  sandbox-switch VER   Switch active sandbox to VER (timestamp)"
    echo "  sandbox-rollback     Revert to the previous sandbox"
    echo "  sandbox-cleanup      Remove old sandboxes (keep $KEEP_VERSIONS)"
    echo "  purge-sifs           Remove all SIF files"
    echo ""
    echo "SIF commands (legacy):"
    echo "  list              List SIF versions"
    echo "  switch VERSION    Switch active SIF"
    echo "  rollback          Revert to previous SIF"
    echo "  cleanup           Remove old SIFs"
    echo "  build [NAME]      Build new SIF from .def"
    echo "  deploy            Deploy active SIF to production"
    echo "  verify            Verify SIF integrity"
    echo ""
    echo "Other:"
    echo "  status            Show current container state"
    echo "  rotate            Cleanup sandboxes (for cron)"
    echo ""
    echo "Environment:"
    echo "  SCITEX_CONTAINERS_DIR  Container directory (default: /opt/scitex/singularity)"
    echo "  SCITEX_KEEP_VERSIONS   Versions to keep (default: 5)"
    echo ""
}

# Dispatch
case "${1:-help}" in
status) cmd_status ;;
sandbox-list) cmd_sandbox_list ;;
sandbox-switch) cmd_sandbox_switch "${2:-}" ;;
sandbox-rollback) cmd_sandbox_rollback ;;
sandbox-cleanup) cmd_sandbox_cleanup ;;
purge-sifs) cmd_purge_sifs ;;
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
