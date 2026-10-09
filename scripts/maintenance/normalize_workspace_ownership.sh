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
#   The same failure mode hits the uv cache, which lives OUTSIDE the
#   workspace: measured 2026-10-09, pytest-matrix py3.13 died at
#   `Install dependencies` with `Failed to initialize cache at
#   /github/home/.cache/uv` + `Permission denied (os error 13)` — a
#   root-owned cache left by a prior job on the same persistent runner.
#   No workflow sets UV_CACHE_DIR (only deployment/docker compose does),
#   so astral-sh/setup-uv resolves the default exactly like uv does
#   ($UV_CACHE_DIR, else $XDG_CACHE_HOME/uv, else $HOME/.cache/uv, i.e.
#   /github/home/.cache/uv on container-path runners). This script
#   normalizes those same candidates best-effort.
#
#   This script chowns the workspace AND the uv cache dir back to the
#   invoking user. It is
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
        echo_warn "dir not found: $dir (skipping)"
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
# uv_cache_dirs
#   Print the uv cache candidates uv / astral-sh/setup-uv would use, one
#   per line, deduplicated. Resolution order mirrors uv: $UV_CACHE_DIR when
#   set, else $XDG_CACHE_HOME/uv, else $HOME/.cache/uv — plus the
#   container-path runner HOME (/github/home/.cache/uv), which can differ
#   from this shell's $HOME when steps run inside a job container while
#   the cache dir is mounted from the runner host. Callers normalize only
#   candidates that exist, so emitting an absent path is a silent skip.
#   Never fails — returns 0 in all cases.
# ---------------------------------------------------------------------------
uv_cache_dirs() {
    local seen="|"
    local d=""
    if [ -n "${UV_CACHE_DIR:-}" ]; then
        printf '%s\n' "${UV_CACHE_DIR}"
        seen="|${UV_CACHE_DIR}|"
    fi
    if [ -n "${XDG_CACHE_HOME:-}" ]; then
        d="${XDG_CACHE_HOME}/uv"
    elif [ -n "${HOME:-}" ]; then
        d="${HOME}/.cache/uv"
    else
        d="/root/.cache/uv"
    fi
    case "$seen" in
        *"|$d|"*) ;;
        *) printf '%s\n' "$d"; seen="${seen}${d}|" ;;
    esac
    d="/github/home/.cache/uv"
    case "$seen" in
        *"|$d|"*) ;;
        *) printf '%s\n' "$d" ;;
    esac
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
    # uv cache: explicit UV_CACHE_DIR must be listed and normalizable.
    local uvcache="$tmp/uvcache"
    mkdir -p "$uvcache"
    touch "$uvcache/probe"
    if ! UV_CACHE_DIR="$uvcache" uv_cache_dirs | grep -qx "$uvcache"; then
        echo_error "self-test: UV_CACHE_DIR candidate missing from uv_cache_dirs"
        return 1
    fi
    UV_CACHE_DIR="$uvcache" normalize "$uvcache" >/dev/null || {
        echo_error "self-test: uv cache normalize returned non-zero"
        return 1
    }
    owner="$(stat -c '%u:%g' "$uvcache/probe")"
    if [ "$owner" != "$want" ]; then
        echo_error "self-test: uv cache probe owned by $owner, want $want"
        return 1
    fi
    # Default candidates must be listed even when UV_CACHE_DIR is unset.
    if ! UV_CACHE_DIR="" uv_cache_dirs | grep -qx "${HOME:-/root}/.cache/uv\|${XDG_CACHE_HOME:-}/uv\|/github/home/.cache/uv"; then
        echo_error "self-test: default uv cache candidate missing"
        return 1
    fi
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

# uv cache: same root-ownership failure mode, one dir outside the workspace.
# Best-effort, never fails: absent candidates are skipped silently (hosted
# runners have no /github/home), existing ones go through normalize() which
# always returns 0. Keeps the script's always-exit-0 contract so callers
# still need no `|| true`.
_uv_dir=""
while IFS= read -r _uv_dir; do
    [ -n "$_uv_dir" ] || continue
    if [ -d "$_uv_dir" ]; then
        normalize "$_uv_dir"
    fi
done < <(uv_cache_dirs)
exit 0
