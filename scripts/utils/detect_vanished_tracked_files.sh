#!/bin/bash
# Detect tracked files that have vanished from a checkout's working tree.
#
# Usage: ./scripts/utils/detect_vanished_tracked_files.sh [CHECKOUT ...]
#   CHECKOUT   path to a git checkout (default: $SCITEX_HUB_CHECKOUTS, else this repo)
#
# Environment:
#   SCITEX_HUB_CHECKOUTS   space-separated checkouts to inspect when no argument
#                          is given. Default: the repo this script lives in.
#   MAX_LISTED             how many missing paths to print per checkout (default 20)
#
# Exit codes are DECLARED, not improvised. 1 and 2 already mean "generic failure"
# and "usage error" in every CLI framework, so a missing verb or a typo would
# impersonate a domain answer if we reused them:
#   0   every tracked file is present in every checkout inspected
#   2   usage error (unreadable argument, not a git checkout)
#   10  FILES ARE MISSING — the condition this script exists to find
#
# WHY THIS EXISTS. On 2026-08-09 the shared main checkout silently lost 3,434
# tracked files -- all of tests/, static/ and src/ -- and nobody noticed FOR THREE
# DAYS. Nothing was watching, so the first symptom was unrelated work failing, and
# by then the forensic trail was cold. Six days later the cause is still not
# established (hub-main-checkout-lost-3434-tracked-files-20260809).
#
# WHY IT DOES NOT RUN IN CI, which is the trap worth writing down. Every instinct
# says "add a CI job". CI clones a FRESH checkout on every run, so a CI job would
# inspect a tree that is intact BY CONSTRUCTION and report green forever, no matter
# how badly a long-lived host checkout had rotted. The check would be correct and
# its SUBJECT would be wrong -- a gate that cannot fail. This defect is a property
# of the LONG-LIVED CHECKOUT, so the detector belongs on the hosts that hold one.
#
# WHY `ls-files --deleted` AND NOT A SWEEP. It compares the INDEX against the
# working tree, so it reports exactly "files git is tracking that are not on disk".
# It needs no baseline file, no stored manifest and no state carried between runs
# -- git already holds the ground truth. It also cannot false-positive on ignored
# or untracked files, which a find/diff sweep would.

set -uo pipefail

MAX_LISTED="${MAX_LISTED:-20}"

EXIT_OK=0
EXIT_USAGE=2
EXIT_FILES_MISSING=10

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
    exit "$EXIT_OK"
fi

# Default target: whatever the operator configured, else the repo holding this
# script (resolved from the script's own location, so a cron entry needs no cwd).
if [ "$#" -gt 0 ]; then
    CHECKOUTS=("$@")
elif [ -n "${SCITEX_HUB_CHECKOUTS:-}" ]; then
    read -r -a CHECKOUTS <<< "$SCITEX_HUB_CHECKOUTS"
else
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    CHECKOUTS=("$(cd -- "$SCRIPT_DIR/../.." && pwd)")
fi

any_missing=0

for checkout in "${CHECKOUTS[@]}"; do
    if [ ! -d "$checkout" ]; then
        echo "ERROR: not a directory: $checkout" >&2
        echo "  Pass a path to a git checkout, or set SCITEX_HUB_CHECKOUTS." >&2
        exit "$EXIT_USAGE"
    fi

    if ! git -C "$checkout" rev-parse --git-dir >/dev/null 2>&1; then
        echo "ERROR: not a git checkout: $checkout" >&2
        echo "  This script compares git's index against the working tree, so it" >&2
        echo "  needs a checkout. Nothing was inspected." >&2
        exit "$EXIT_USAGE"
    fi

    # The whole check. Empty output is the healthy state.
    missing="$(git -C "$checkout" ls-files --deleted)"

    if [ -z "$missing" ]; then
        tracked="$(git -C "$checkout" ls-files | wc -l)"
        echo "OK   $checkout — $tracked tracked file(s), none missing"
        continue
    fi

    any_missing=1
    count="$(printf '%s\n' "$missing" | wc -l)"
    tracked="$(git -C "$checkout" ls-files | wc -l)"

    echo "MISSING   $checkout — $count of $tracked tracked file(s) are NOT on disk"
    printf '%s\n' "$missing" | head -n "$MAX_LISTED" | sed 's/^/    /'
    if [ "$count" -gt "$MAX_LISTED" ]; then
        echo "    ... and $((count - MAX_LISTED)) more (raise MAX_LISTED to see them)"
    fi
    echo "  RECOVER:  git -C $checkout restore ."
    echo "  Then find out WHY before trusting the checkout again: git's own reflog"
    echo "  showed NO ref-moving operation during the 2026-08-09 disappearance, so a"
    echo "  git command is not the likely cause. Check mounts and container restarts"
    echo "  first — whole subtrees vanishing and returning intact is the signature of"
    echo "  a filesystem view changing, not of a delete."
done

if [ "$any_missing" -ne 0 ]; then
    exit "$EXIT_FILES_MISSING"
fi

exit "$EXIT_OK"
