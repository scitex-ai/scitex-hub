#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-07-18 00:00:00 (ywatanabe)"
# File: ./scripts/maintenance/check_absolute_symlinks.sh

# ============================================================================
# Absolute-Symlink Guard — reject tracked symlinks with ABSOLUTE targets
# ============================================================================
# Location: /scripts/maintenance/check_absolute_symlinks.sh
#
# Purpose:
#   A tracked symlink whose target is an ABSOLUTE path (starts with "/") is a
#   host-specific artifact. It breaks `git pull` / checkout on every other host
#   (NAS, CI, other agent containers) because the target does not exist there.
#   Two real incidents motivated this guard:
#     * PR #409  — node_modules -> /home/ywatanabe/proj/scitex-cloud/node_modules
#     * dotfiles — 2026-07-12 P0, src/.scitex -> a Spartan-only absolute path
#
#   This is the ROOT-CAUSE guard: it fails loudly (non-zero) if ANY tracked
#   symlink target is absolute, so the class of bug cannot recur.
#
# What it does NOT trust:
#   The working tree. A symlink can be tracked in the index but replaced on
#   disk with a regular file (or missing). We therefore read symlink targets
#   from the git INDEX (`git ls-files -s` + `git cat-file`), never from `ls`.
#   In a pre-commit hook the index reflects the STAGED content; in CI (after a
#   fresh checkout) the index reflects HEAD. One code path covers both.
#
# Usage:
#   ./scripts/maintenance/check_absolute_symlinks.sh            # scan + report
#   ./scripts/maintenance/check_absolute_symlinks.sh --quiet    # exit code only
#   ./scripts/maintenance/check_absolute_symlinks.sh --self-test # red/green proof
#
# Exit codes:
#   0  no tracked symlink has an absolute target (clean)
#   1  at least one violation found (or --self-test failed)

set -u

GRAY='\033[0;90m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }

# ---------------------------------------------------------------------------
# scan_repo <git-dir>
#   Print one "path\ttarget" line per tracked symlink whose target is
#   ABSOLUTE. Reads the index (not the working tree). Returns the violation
#   count via the global VIOLATIONS.
# ---------------------------------------------------------------------------
VIOLATIONS=0
scan_repo() {
    local dir="$1"
    VIOLATIONS=0

    # `git ls-files -s -z` emits, per entry, "<mode> <sha> <stage>\t<path>\0".
    # mode 120000 == symlink; the blob content is the symlink target string.
    local entry mode rest sha path target
    while IFS= read -r -d '' entry; do
        mode="${entry%% *}"
        [ "$mode" = "120000" ] || continue
        rest="${entry#* }"            # "<sha> <stage>\t<path>"
        sha="${rest%% *}"             # "<sha>"
        path="${entry#*$'\t'}"        # everything after the tab
        target="$(git -C "$dir" cat-file -p "$sha" 2>/dev/null)"
        case "$target" in
            /*)
                printf '%s\t%s\n' "$path" "$target"
                VIOLATIONS=$((VIOLATIONS + 1))
                ;;
        esac
    done < <(git -C "$dir" ls-files -s -z)

    return 0
}

# ---------------------------------------------------------------------------
# --self-test : prove RED-before-GREEN in an ISOLATED throwaway repo.
#   1. absolute-target symlink  => guard MUST report a violation (RED)
#   2. relative-target symlink  => guard MUST be clean            (GREEN)
# Never touches the real repo index.
# ---------------------------------------------------------------------------
run_self_test() {
    local tmp rc=0
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN

    git -C "$tmp" init -q
    git -C "$tmp" config user.email test@example.com
    git -C "$tmp" config user.name test
    echo "real" >"$tmp/real.txt"

    # (1) RED: absolute-target symlink must be caught.
    ln -s /home/someone/abs/target "$tmp/bad_link"
    git -C "$tmp" add -A
    scan_repo "$tmp" >/dev/null
    if [ "$VIOLATIONS" -ne 1 ]; then
        echo_error "self-test FAILED: absolute-target symlink not caught (got $VIOLATIONS)"
        return 1
    fi
    echo_success "self-test RED ok: absolute-target symlink correctly rejected"

    # (2) GREEN: replace with a relative-target symlink; must pass.
    git -C "$tmp" rm -q --cached bad_link
    rm -f "$tmp/bad_link"
    ln -s real.txt "$tmp/good_link"
    git -C "$tmp" add -A
    scan_repo "$tmp" >/dev/null
    if [ "$VIOLATIONS" -ne 0 ]; then
        echo_error "self-test FAILED: relative-target symlink wrongly rejected"
        return 1
    fi
    echo_success "self-test GREEN ok: relative-target symlink correctly accepted"

    return $rc
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
MODE="${1:-normal}"

if [ "$MODE" = "--self-test" ]; then
    run_self_test
    exit $?
fi

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$GIT_ROOT" ]; then
    echo_error "not inside a git repository"
    exit 1
fi

# Capture violations (path<TAB>target lines). scan_repo runs in a subshell
# here (process substitution), so its global VIOLATIONS does NOT propagate —
# derive the count from the captured lines instead.
mapfile -t HITS < <(scan_repo "$GIT_ROOT")
VIOLATIONS=${#HITS[@]}

if [ "$VIOLATIONS" -eq 0 ]; then
    if [ "$MODE" != "--quiet" ]; then
        echo "🔗 Tracked symlinks: [OK] no absolute-target symlinks"
    fi
    exit 0
fi

# Violations found.
if [ "$MODE" = "--quiet" ]; then
    exit 1
fi

echo -e "${RED}[FAIL] $VIOLATIONS tracked symlink(s) point to an ABSOLUTE path.${NC}"
echo -e "       Absolute targets are host-specific and break \`git pull\` /"
echo -e "       checkout on every other host (NAS, CI, other containers)."
echo ""
for line in "${HITS[@]}"; do
    p="${line%%$'\t'*}"
    t="${line#*$'\t'}"
    echo -e "  ${RED}${p}${NC}"
    echo -e "      -> ${t}"
done
echo ""
echo -e "  Fix: point the symlink at a RELATIVE target, or drop it entirely:"
echo -e "      git rm --cached <path>        # untrack (keep the file locally)"
echo -e "      # or re-create with a repo-relative target and re-add"
echo ""
echo -e "  Context: PR #409 (node_modules), dotfiles P0 2026-07-12 (src/.scitex)."

exit 1

# EOF
