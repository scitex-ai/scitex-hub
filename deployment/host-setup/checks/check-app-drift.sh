#!/bin/bash
# Sibling-app clone drift — is the code we are SERVING the code we think it is?
#
# WHY THIS EXISTS (2026-08-10). scitex-hub does not install its sibling apps
# from PyPI. .scitex-apps.json pins `git_ref: develop` for all of them, and
# install_apps.sh clones that BRANCH into <container>/.apps/<name>, editable.
# That clone is refreshed ONLY at container start. So a container that has been
# up for a week is serving a week-old snapshot of somebody else's develop, and
# nothing anywhere said so.
#
# Measured the day this was written: prod's scitex-cards clone sat at 5964e22
# (2026-08-03) while the fix everyone believed was live had been RELEASED TWICE
# (v0.32.2, v0.32.3) days earlier. Three separate incidents that evening were
# the same shape — a fix reported as delivered, a fix another agent was blocked
# on, and that one. Each was diagnosed only by someone SSHing in and reading a
# SHA by hand.
#
# This check is deliberately READ-ONLY. It never fetches into a checkout, never
# resets, never restarts anything. Refreshing prod means taking the branch tip,
# which is a decision with a blast radius; this only makes the decision visible.
#
# THREE-VALUED BY CONSTRUCTION (constitution §2): every app reports OK, DRIFT,
# or UNKNOWN. "Could not reach the remote" is UNKNOWN and is NEVER folded into
# OK — a check that reports healthy when it could not measure is the
# gate-that-cannot-fail, and the whole reason this file exists is that silence
# read as health for seven days.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
# Overridable so this can be exercised against a real deployment without being
# copied into that deployment's checkout first. Defaults to the repo it ships in.
MANIFEST="${APP_DRIFT_MANIFEST:-${PROJECT_ROOT}/.scitex-apps.json}"

# shellcheck disable=SC1091
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# Network calls are bounded so a slow or unreachable remote degrades this
# section to UNKNOWN instead of stalling `make status`, which runs its sections
# in parallel and is supposed to be fast enough to actually get read.
LS_REMOTE_TIMEOUT="${APP_DRIFT_LS_REMOTE_TIMEOUT:-8}"
# A clone older than this is called out loudly rather than merely listed.
STALE_DAYS="${APP_DRIFT_STALE_DAYS:-2}"

echo "📦 Sibling app clones (deployed code vs its tracked branch):"

if [ ! -f "$MANIFEST" ]; then
    echo -e "  ${YELLOW}[UNKNOWN] no manifest at ${MANIFEST}${NC}"
    echo    "           Without it we cannot tell which apps are deployed."
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "  ${YELLOW}[UNKNOWN] python3 not available to parse the manifest${NC}"
    echo    "           Install python3, or read .scitex-apps.json by hand."
    exit 0
fi

# name<TAB>git_url<TAB>git_ref, one app per line. Parse failures are surfaced,
# never swallowed into an empty list that would render as "nothing to report".
APPS=$(python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as fh:
        data = json.load(fh)
except Exception as exc:
    print("PARSE_ERROR\t%s" % exc, end="")
    sys.exit(0)
for app in data.get("apps", []):
    print("\t".join([
        app.get("name", "?"),
        app.get("git_url", ""),
        app.get("git_ref", ""),
    ]))
' "$MANIFEST" 2>&1)

if [[ "$APPS" == PARSE_ERROR* ]]; then
    echo -e "  ${RED}[UNKNOWN] manifest is unreadable: ${APPS#PARSE_ERROR	}${NC}"
    echo    "           Fix .scitex-apps.json — until then no app version is known."
    exit 0
fi

if [ -z "$APPS" ]; then
    echo -e "  ${YELLOW}[UNKNOWN] manifest lists no apps${NC}"
    exit 0
fi

# Which container to read the deployed clones from. Prod is the one that
# matters; fall back to staging, then dev, and SAY which one was used — a
# version reported without naming the environment it came from is how "it is
# fixed" gets said about the wrong box.
CONTAINER=""
for candidate in scitex-hub-prod-django-1 scitex-hub-staging-django-1 scitex-hub-dev-django-1; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$candidate"; then
        CONTAINER="$candidate"
        break
    fi
done

if [ -z "$CONTAINER" ]; then
    echo -e "  ${YELLOW}[UNKNOWN] no django container running — cannot read deployed clones${NC}"
    echo    "           Start an environment (make env=dev start) to see app versions."
    exit 0
fi

UPTIME=$(docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null |
    awk -F'\t' -v c="$CONTAINER" '$1==c{print $2}')
echo "  source: ${CONTAINER} (${UPTIME:-uptime unknown})"

drift_found=0
unknown_found=0

while IFS=$'\t' read -r name git_url git_ref; do
    [ -z "$name" ] && continue

    # `-c safe.directory` because the clone is owned by the image's build user
    # while this exec may run as another; without it git refuses with "dubious
    # ownership" and we would misread a healthy clone as missing.
    clone="/app/.apps/${name}"
    read -r local_sha local_date < <(
        docker exec "$CONTAINER" git \
            -C "$clone" -c "safe.directory=${clone}" \
            log -1 --format='%H %cs' 2>/dev/null || echo ""
    )

    if [ -z "${local_sha:-}" ]; then
        echo -e "  ${YELLOW}[UNKNOWN]${NC} ${name}: no readable git clone at ${clone}"
        unknown_found=1
        continue
    fi

    if [ -z "$git_url" ] || [ -z "$git_ref" ]; then
        echo -e "  ${YELLOW}[UNKNOWN]${NC} ${name}: manifest has no git_url/git_ref; running ${local_sha:0:9} (${local_date})"
        unknown_found=1
        continue
    fi

    remote_sha=$(timeout "$LS_REMOTE_TIMEOUT" git ls-remote "$git_url" "$git_ref" 2>/dev/null | awk '{print $1}' | head -1)

    # Age is computed from the LOCAL commit date and printed on every line,
    # drifted or not. A count of commits behind reads as a number to schedule;
    # "code from 2026-08-03" reads as a fact to act on, and the date is what
    # ended the confusion in all three incidents that prompted this check.
    age_days="?"
    if [ -n "${local_date:-}" ]; then
        local_epoch=$(date -d "$local_date" +%s 2>/dev/null || echo "")
        if [ -n "$local_epoch" ]; then
            age_days=$(( ( $(date +%s) - local_epoch ) / 86400 ))
        fi
    fi

    if [ -z "$remote_sha" ]; then
        echo -e "  ${YELLOW}[UNKNOWN]${NC} ${name}: running ${local_sha:0:9} (${local_date}, ${age_days}d old) — could not reach ${git_url}"
        echo    "            Not assuming this is current. Re-run when the network is back."
        unknown_found=1
    elif [ "$remote_sha" = "$local_sha" ]; then
        echo -e "  ${GREEN}[OK]${NC}      ${name}: ${local_sha:0:9} (${local_date}, ${age_days}d old) == ${git_ref} tip"
    else
        drift_found=1
        if [ "$age_days" != "?" ] && [ "$age_days" -ge "$STALE_DAYS" ]; then
            echo -e "  ${RED}[DRIFT]${NC}   ${name}: serving code from ${local_date} (${age_days} days old)"
        else
            echo -e "  ${YELLOW}[DRIFT]${NC}   ${name}: serving code from ${local_date} (${age_days}d old)"
        fi
        echo    "            running ${local_sha:0:9}, ${git_ref} tip is ${remote_sha:0:9}"
    fi
done <<<"$APPS"

if [ "$drift_found" -eq 1 ]; then
    echo ""
    echo -e "  ${YELLOW}Clones refresh ONLY at container start, and they track a BRANCH${NC}"
    echo    "  (git_ref in .scitex-apps.json), not a release tag. So restarting"
    echo    "  takes whatever is on that branch right now — the fix you want AND"
    echo    "  everything else merged since. Check the upstream branch is green"
    echo    "  before restarting to pick something up."
    echo    "  Tracked: hub-prod-tracks-app-develop-branches-and-only-syncs-at-restart-20260810"
fi

if [ "$unknown_found" -eq 1 ]; then
    echo ""
    echo -e "  ${YELLOW}Some apps could not be measured (UNKNOWN above).${NC}"
    echo    "  UNKNOWN is not OK: those versions are simply not known right now."
fi

exit 0
