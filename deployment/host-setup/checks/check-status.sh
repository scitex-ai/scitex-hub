#!/bin/bash
# Master Status Check — Async Orchestrator
# Runs all sections in parallel; each prints as an atomic chunk.
# This is the single reliable source for admin's short-term memory.
#
# WHAT TO EDIT: not this file. The sections live in sections.sh, which
# `make status-live` iterates too — adding a check here alone is how disk
# checking ended up in one surface and not the other (see sections.sh).
#
# HOW IT ENDS, and why. Sections print in COMPLETION order, so a [FAIL] lands
# at an unpredictable position among ~15 chunks and the eye settles on the
# last line. Until 2026-09-05 that last line was `date`, and every section's
# exit code was discarded (`|| true`): check_disk_space.sh computes a real
# 0/1/2 verdict and says in its header that it GATES, and this file threw
# that verdict away, so `make status` exited 0 with a full disk on screen.
# A check whose failure nothing reads is not a check. Now:
#
#   - every section's exit code is kept (<name>.rc beside its output),
#   - the run ends with ONE summary line counting FAIL / WARN / OK by section,
#     naming the failing and warning sections, in registry order,
#   - and the script exits 1 when any section FAILED, 0 otherwise. WARN does
#     not gate (that is the disk check's own convention: 2 = warn, 1 = fail).
#
# A section FAILS when its output carries [FAIL] or [CRIT…], or it exited 1,
# or it exited with any other non-zero code that is not a WARN (a section that
# could not run at all — missing interpreter, 127 — is a failure the admin
# must see, not an empty chunk). A section WARNS when its output carries
# [WARN] or [UNKNOWN], or it exited 2. Tokens win over codes: a section that
# prints [FAIL] and exits 0 still counts as a failure.
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

# Run a section: capture output AND exit code to temp files, then print the
# output atomically. The `|| true` keeps `set -o pipefail` from ending the
# orchestrator on the first red section; the verdict is not lost — it is in
# the .rc file and read by the summary below.
run_section() {
    local name="$1"
    shift
    local rc=0
    "$@" >"${TMPDIR_STATUS}/${name}" 2>&1 || rc=$?
    echo "$rc" >"${TMPDIR_STATUS}/${name}.rc"
    cat "${TMPDIR_STATUS}/${name}"
    echo ""
}

# Classify one finished section from its captured output and exit code.
# Prints FAIL, WARN or OK.
section_verdict() {
    local name="$1"
    local out="${TMPDIR_STATUS}/${name}"
    local rc
    rc=$(cat "${TMPDIR_STATUS}/${name}.rc" 2>/dev/null || echo 1)
    if grep -q -E '\[FAIL\]|\[CRIT' "$out" 2>/dev/null; then
        echo FAIL
    elif [ "$rc" = "1" ]; then
        echo FAIL
    elif grep -q -E '\[WARN\]|\[UNKNOWN\]' "$out" 2>/dev/null; then
        echo WARN
    elif [ "$rc" = "2" ]; then
        echo WARN
    elif [ "$rc" != "0" ]; then
        echo FAIL
    else
        echo OK
    fi
}

# ── Launch every registered section in parallel ────────────
registered=()
while IFS=$'\t' read -r name command; do
    [ -n "$name" ] || continue
    registered+=("$name")
    run_section "$name" "$command" &
done < <(status_sections)
wait

# ── Summary: the last thing on screen is the verdict, not the date ──
fail_names=()
warn_names=()
ok_count=0
for name in "${registered[@]}"; do
    case "$(section_verdict "$name")" in
        FAIL) fail_names+=("$name") ;;
        WARN) warn_names+=("$name") ;;
        *) ok_count=$((ok_count + 1)) ;;
    esac
done

echo ""
echo "SUMMARY: ${#fail_names[@]} FAIL, ${#warn_names[@]} WARN, ${ok_count} OK of ${#registered[@]} sections"
if [ "${#fail_names[@]}" -gt 0 ]; then
    echo "  FAIL: ${fail_names[*]}"
fi
if [ "${#warn_names[@]}" -gt 0 ]; then
    echo "  WARN: ${warn_names[*]}"
fi
date

# ── Exit code: `make status` gates on FAIL ──────────────────
if [ "${#fail_names[@]}" -gt 0 ]; then
    exit 1
fi
exit 0
