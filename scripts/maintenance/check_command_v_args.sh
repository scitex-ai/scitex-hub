#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-08-05 00:00:00 (ywatanabe)"
# File: ./scripts/maintenance/check_command_v_args.sh

# ============================================================================
# `command -v` Argument Guard — reject a guard that cannot fail
# ============================================================================
# Location: /scripts/maintenance/check_command_v_args.sh
#
# Purpose:
#   `command -v` takes command NAMES and IGNORES every trailing argument. So
#
#       command -v python3 -m pip >/dev/null 2>&1 || apt-get install python3-pip
#
#   does not test pip. It tests `python3`, and returns 0 on any machine that
#   ships python3 — which is all of them. The install it guards never runs.
#   Proven with a control rather than by reading:
#
#       command -v python3 -m NONEXISTENT_MODULE   ->  rc 0
#
#   Motivating incident: deployment/host-setup/provision-compute-node.sh (PR
#   #553, fixed in #554). On a bare Ubuntu node the guarded apt step was
#   skipped and `python3 -m venv` then died. It passed human review, and it
#   passed on the one host it was ever run against, because that host happened
#   to have pip preinstalled — so the gate was never exercised on the case it
#   existed for. That is the signature of this whole class: it is invisible
#   until you meet the machine it was written for.
#
#   Test a MODULE by running or importing it:
#       python3 -m pip --version    >/dev/null 2>&1 || need="$need python3-pip"
#       python3 -c 'import ensurepip' >/dev/null 2>&1 || need="$need python3-venv"
#
# What it does NOT trust:
#   * The working tree — it reads blobs from the git INDEX, so in a pre-commit
#     hook it sees STAGED content and in CI it sees HEAD. One code path, both.
#   * A silent zero — it prints how many files it actually scanned. A clean
#     result over a corpus of 0 files is not clean, it is vacuous, and this
#     script says so and exits non-zero rather than reporting success.
#
# Deliberately NOT flagged (a gate with false positives gets disabled):
#   command -v foo                     # the correct form
#   command -v foo >/dev/null 2>&1     # redirections are not arguments
#   command -v foo || fallback         # operators are not arguments
#   # command -v foo -m bar            # full-line comments (incl. this file's)
#
# Usage:
#   ./scripts/maintenance/check_command_v_args.sh              # scan + report
#   ./scripts/maintenance/check_command_v_args.sh --quiet      # exit code only
#   ./scripts/maintenance/check_command_v_args.sh --self-test  # red/green proof
#
# Exit codes:
#   0  no `command -v` call carries trailing arguments (clean)
#   1  at least one violation found, or the scan was vacuous, or --self-test
#      failed

set -u

GRAY='\033[0;90m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }

# `command -v` <name> <another-token>, where the trailing token is NOT a
# redirection (> < digit), a control operator (; | &), or a subshell close.
# Written with a character class rather than the literal string so this file
# does not match itself.
PATTERN='command[[:space:]]+-v[[:space:]]+[^[:space:];|&)]+[[:space:]]+[^[:space:];|&)>=<0-9]'

# ---------------------------------------------------------------------------
# scan_repo <git-dir>
#   Print one "path:line:content" per violation. Emits a trailing
#   "SCANNED<TAB>n" line so the caller can prove the corpus was non-empty —
#   the count cannot be returned in a global because the loop that produces it
#   runs in a subshell (process substitution).
# ---------------------------------------------------------------------------
scan_repo() {
    local dir="$1"
    local scanned=0
    local entry mode rest sha path

    while IFS= read -r -d '' entry; do
        mode="${entry%% *}"
        # Regular files only (100644 / 100755); skip symlinks and gitlinks.
        case "$mode" in
            100644 | 100755) ;;
            *) continue ;;
        esac
        rest="${entry#* }"
        sha="${rest%% *}"
        path="${entry#*$'\t'}"

        # Shell corpus: by extension, or any tracked executable (catches the
        # extensionless hooks and bin/ scripts that also run as shell).
        case "$path" in
            *.sh | *.bash) ;;
            *) [ "$mode" = "100755" ] || continue ;;
        esac

        scanned=$((scanned + 1))
        # Drop full-line comments BEFORE matching: this file, and the fix that
        # motivated it, both document the bad form in prose.
        git -C "$dir" cat-file -p "$sha" 2>/dev/null \
            | grep -nE "$PATTERN" \
            | grep -vE '^[0-9]+:[[:space:]]*#' \
            | while IFS= read -r hit; do printf '%s:%s\n' "$path" "$hit"; done
    done < <(git -C "$dir" ls-files -s -z)

    printf 'SCANNED\t%s\n' "$scanned"
}

# ---------------------------------------------------------------------------
# --self-test : prove RED-before-GREEN in an ISOLATED throwaway repo, and
#   prove the legitimate forms are NOT flagged. A guard that fires on correct
#   code gets switched off, so the false-positive half is not optional.
# ---------------------------------------------------------------------------
run_self_test() {
    local tmp hits n
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN

    git -C "$tmp" init -q
    git -C "$tmp" config user.email test@example.com
    git -C "$tmp" config user.name test

    # (1) RED: the real defect must be caught.
    printf '#!/bin/bash\ncommand -v python3 -m pip >/dev/null 2>&1 || echo no\n' \
        >"$tmp/bad.sh"
    git -C "$tmp" add -A
    hits="$(scan_repo "$tmp" | grep -v '^SCANNED')"
    n="$(printf '%s' "$hits" | grep -c . )"
    if [ "$n" -ne 1 ]; then
        echo_error "self-test FAILED: 'command -v python3 -m pip' not caught (got $n)"
        return 1
    fi
    echo_success "self-test RED ok: trailing-argument form correctly rejected"

    # (2) GREEN: every legitimate form must pass, including full-line comments.
    git -C "$tmp" rm -q --cached bad.sh
    rm -f "$tmp/bad.sh"
    {
        printf '#!/bin/bash\n'
        printf 'command -v foo\n'
        printf 'command -v foo >/dev/null 2>&1\n'
        printf 'command -v foo || echo fallback\n'
        printf 'if command -v foo >/dev/null; then echo yes; fi\n'
        printf '# command -v python3 -m pip   <- documented, not executed\n'
    } >"$tmp/good.sh"
    git -C "$tmp" add -A
    hits="$(scan_repo "$tmp" | grep -v '^SCANNED')"
    n="$(printf '%s' "$hits" | grep -c . )"
    if [ "$n" -ne 0 ]; then
        echo_error "self-test FAILED: legitimate forms wrongly rejected ($n):"
        printf '%s\n' "$hits"
        return 1
    fi
    echo_success "self-test GREEN ok: correct forms and comments correctly accepted"

    return 0
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

mapfile -t RAW < <(scan_repo "$GIT_ROOT")

SCANNED=0
HITS=()
for line in "${RAW[@]}"; do
    case "$line" in
        "SCANNED"$'\t'*) SCANNED="${line#*$'\t'}" ;;
        "") ;;
        *) HITS+=("$line") ;;
    esac
done
VIOLATIONS=${#HITS[@]}

# A pass over an empty corpus is not a pass. Say so instead of printing OK.
if [ "$SCANNED" -eq 0 ]; then
    echo_error "vacuous scan: 0 shell files were read, so a clean result proves nothing"
    echo_error "  check that this is the repo root and that shell files are TRACKED"
    exit 1
fi

if [ "$VIOLATIONS" -eq 0 ]; then
    if [ "$MODE" != "--quiet" ]; then
        echo "🛡  command -v guards: [OK] no trailing arguments (${SCANNED} shell files scanned)"
    fi
    exit 0
fi

if [ "$MODE" = "--quiet" ]; then
    exit 1
fi

echo -e "${RED}[FAIL] ${VIOLATIONS} \`command -v\` call(s) carry trailing arguments.${NC}"
echo -e "       \`command -v\` ignores them, so the guard returns 0 whenever the"
echo -e "       NAME exists and the branch it protects never runs."
echo ""
for line in "${HITS[@]}"; do
    # printf '%s' for the LINE, never echo -e: a matched line ending in a
    # backslash (a shell line continuation, which is exactly what the
    # motivating instance ends with) makes echo -e swallow the colour reset and
    # print a literal \033[0m. Source content is data, not a format string.
    printf '  %b%s%b\n' "$RED" "$line" "$NC"
done
echo ""
echo -e "  Fix: test the module by RUNNING it, not by naming it:"
echo -e "      python3 -m pip --version      >/dev/null 2>&1 || need=\"\$need python3-pip\""
echo -e "      python3 -c 'import ensurepip' >/dev/null 2>&1 || need=\"\$need python3-venv\""
echo ""
echo -e "  Scanned ${SCANNED} tracked shell files."
echo -e "  Context: provision-compute-node.sh (PR #553, fixed in #554)."

exit 1

# EOF
