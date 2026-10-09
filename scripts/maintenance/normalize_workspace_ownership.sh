#!/bin/bash
# -*- coding: utf-8 -*-
# File: ./scripts/maintenance/normalize_workspace_ownership.sh

# ============================================================================
# Workspace-Ownership Normalizer — keep persistent self-hosted runners clean
# ============================================================================
# Location: /scripts/maintenance/normalize_workspace_ownership.sh
#
# Purpose:
#   Persistent self-hosted runners REUSE the work dir across jobs. Any
#   root-owned file left behind breaks the NEXT job's checkout cleanup
#   (`git clean -ffdx`) with `EACCES: permission denied, unlink ...`.
#   Measured incidents on scitex-ci-04 / org runners: root-owned
#   `.pytest_cache/.gitignore`, `.agent-communication/codex-hub.md`, and
#   `data/users/*` dirs. Root ownership arrives via the job-container
#   default user (root unless `--user` maps it), sudo-installed tooling,
#   or an external agent process writing into the work dir as root.
#
#   This script chowns the workspace back to the invoking user. It is
#   cleanup, NOT a check: it ALWAYS exits 0 and must never turn a job red,
#   so callers need no `|| true` (which tests/develop/
#   test_ci_bypasses_are_justified.py would reject without an allowlist
#   entry per workflow file).
#
# Usage (LAST step of every CI job that checks out code on a persistent
# runner — `if: always()` so it runs even when the job fails):
#   bash scripts/maintenance/normalize_workspace_ownership.sh
#   bash scripts/maintenance/normalize_workspace_ownership.sh --self-test
#
# Exit codes:
#   0  always (cleanup must not gate the job; failures print a warning)
#   1  --self-test failed

set -u

GRAY='\033[0;90m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warn() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }

# ---------------------------------------------------------------------------
# normalize <dir>
#   chown <dir> back to the invoking uid:gid. Prefers passwordless sudo
#   (needed when root-owned files exist); falls back to plain chown
#   (a no-op for own files, e.g. inside uid-mapped job containers without
#   sudo). Never fails — returns 0 in all cases.
# ---------------------------------------------------------------------------
normalize() {
    local dir="$1"
    local owner
    owner="$(id -u):$(id -g)"
    if [ ! -d "$dir" ]; then
        echo_warn "workspace dir not found: $dir (skipping)"
        return 0
    fi
    if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
        if sudo -n chown -R "$owner" "$dir" 2>/dev/null; then
            echo_success "ownership restored via sudo: $dir -> $owner"
        else
            echo_warn "sudo chown incomplete on $dir (continuing)"
        fi
    else
        if chown -R "$owner" "$dir" 2>/dev/null; then
            echo_info "ownership restored without sudo: $dir -> $owner"
        else
            echo_warn "no passwordless sudo and unowned files remain under $dir (continuing)"
        fi
    fi
    return 0
}

# ---------------------------------------------------------------------------
# --self-test: prove the script normalizes and never fails
# ---------------------------------------------------------------------------
self_test() {
    local tmp
    tmp="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf '$tmp'" EXIT
    touch "$tmp/probe"
    GITHUB_WORKSPACE="$tmp" normalize "$tmp" >/dev/null || {
        echo_error "self-test: normalize returned non-zero"
        return 1
    }
    local owner
    owner="$(stat -c '%u:%g' "$tmp/probe")"
    local want
    want="$(id -u):$(id -g)"
    if [ "$owner" != "$want" ]; then
        echo_error "self-test: probe owned by $owner, want $want"
        return 1
    fi
    # Missing dir must warn, not fail.
    normalize "$tmp/does-not-exist" >/dev/null || {
        echo_error "self-test: missing dir returned non-zero"
        return 1
    }
    echo_success "self-test: normalize ok ($want), missing dir tolerated"
    return 0
}

if [ "${1:-}" = "--self-test" ]; then
    if self_test; then
        exit 0
    else
        exit 1
    fi
fi

normalize "${GITHUB_WORKSPACE:-$PWD}"
exit 0
