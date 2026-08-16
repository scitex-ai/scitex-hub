#!/bin/bash
# Master Status Check — Async Orchestrator
# Runs all sections in parallel; each prints as an atomic chunk.
# This is the single reliable source for admin's short-term memory.
#
# WHAT TO EDIT: not this file. The sections live in sections.sh, which
# `make status-live` iterates too — adding a check here alone is how disk
# checking ended up in one surface and not the other (see sections.sh).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

SECTIONS_SCRIPT_DIR="${SCRIPT_DIR}"
SECTIONS_PROJECT_ROOT="${PROJECT_ROOT}"
export SECTIONS_SCRIPT_DIR SECTIONS_PROJECT_ROOT
# shellcheck source=deployment/host-setup/checks/sections.sh
source "${SCRIPT_DIR}/sections.sh"

# ── Temp dir for atomic section output ─────────────────────
TMPDIR_STATUS=$(mktemp -d)
trap 'rm -rf "$TMPDIR_STATUS"' EXIT

# Run a section: capture output to temp file, then print atomically
run_section() {
    local name="$1"
    shift
    "$@" >"${TMPDIR_STATUS}/${name}" 2>&1 || true
    cat "${TMPDIR_STATUS}/${name}"
    echo ""
}

# ── Launch every registered section in parallel ────────────
while IFS=$'\t' read -r name command; do
    [ -n "$name" ] || continue
    run_section "$name" "$command" &
done < <(status_sections)

wait

# ── Timestamp ──────────────────────────────────────────────
echo ""
date
