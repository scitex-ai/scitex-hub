#!/bin/bash
# Disk & Inode Headroom — the alarm that was missing on 2026-08-09.
#
# INCIDENT 2026-08-09 — why this file exists:
#   scitex-compute-04's 393G volume reached 100% full — zero bytes free, and
#   92% of its inodes consumed. NOTHING alarmed. The first notice anybody got
#   was
#
#       stat: write error: No space left on device
#
#   raised from inside an unrelated task, by which point the fleet's a2a bus
#   was already answering HTTP 500 with no explanation. `make status` printed
#   a wall of [OK] throughout: the closest thing to a disk metric in the whole
#   tree was check-services.sh reporting how BIG the OpenAlex DB file is, which
#   would have said [OK] at 100% full.
#
#   Repo CLAUDE.md: `make status` "must be a reliable device for loading
#   necessary information to administrator's short-term memory". A full disk
#   plainly qualifies, and was absent.
#
# BYTES AND INODES ARE REPORTED SEPARATELY AND ALARM INDEPENDENTLY.
#   Inode exhaustion fails writes while bytes are still plentiful, and the
#   reverse. A check that watched only bytes would have called 92% inodes
#   healthy right up to the failure. Each volume therefore gets ONE LINE PER
#   METRIC, each carrying its own severity token.
#
# NO SILENT FALLBACK.
#   During the incident `df` itself errored while measuring. A path that cannot
#   be measured is reported [UNKNOWN] and counted as a WARNING — an
#   unmeasurable volume must never read as a healthy one.
#
# Exit codes (this check GATES, it does not merely print):
#   0  every measured volume has headroom
#   1  CRITICAL — a volume is under CRIT_FREE_PCT% free
#   2  WARNING  — a volume is under WARN_FREE_PCT% free, or is unmeasurable
#   `make status` discards these (run_section ends `|| true`); they exist so
#   the same script can gate a deploy step or a cron job.
#
# Called by: make status -> deployment/host-setup/checks/check-status.sh

set -uo pipefail
# `set -e` is deliberately omitted: a check whose entire job is to report
# failures must not die on the first one and truncate its own section.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=/dev/null
# shellcheck disable=SC2034
source "${PROJECT_ROOT}/deployment/host-setup/scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# ── Thresholds: percent of the resource still FREE ─────────
WARN_FREE_PCT=10
CRIT_FREE_PCT=2
WARN_X10=$((WARN_FREE_PCT * 10))
CRIT_X10=$((CRIT_FREE_PCT * 10))

ERRFILE=$(mktemp)
trap 'rm -f "$ERRFILE"' EXIT

critical=0
warnings=0

# Measure one path for one metric. Emits exactly ONE record:
#   OK|<source>|<total>|<free>|<free_pct_x10>|<mount>
#   SKIP|<reason>      filesystem keeps no fixed inode table (btrfs/zfs/…)
#   UNKNOWN|<reason>   unmeasurable — the caller treats this as a WARNING
probe() {
    local path="$1" metric="$2"
    local flag out rc line
    if [ "$metric" = "inodes" ]; then
        flag="-i"
    else
        flag="-k"
    fi
    out=$(df -P "$flag" "$path" 2>"$ERRFILE")
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf 'UNKNOWN|df -P %s %s exited %s: %s\n' "$flag" "$path" "$rc" \
            "$(tr -d '|\n' < "$ERRFILE" | cut -c1-160)"
        return
    fi
    line=$(printf '%s\n' "$out" | awk 'NR > 1 && NF >= 6 { print; exit }')
    if [ -z "$line" ]; then
        printf 'UNKNOWN|df -P %s %s printed no data row\n' "$flag" "$path"
        return
    fi
    printf '%s\n' "$line" | awk -v metric="$metric" '
        {
            src = $1; total = $2; free = $4; mount = $6
            for (i = 7; i <= NF; i++) mount = mount " " $i
            if (total == "-" && metric == "inodes") {
                print "SKIP|" mount " keeps no fixed inode table"
                exit
            }
            if (total !~ /^[0-9]+$/ || free !~ /^[0-9]+$/) {
                print "UNKNOWN|df returned non-numeric " metric " for " mount
                exit
            }
            if (total + 0 == 0) {
                print "UNKNOWN|df reports 0 total " metric " for " mount
                exit
            }
            printf "OK|%s|%s|%s|%d|%s\n", src, total, free,
                int(free * 1000 / total), mount
        }'
}

human_kb() {
    awk -v v="$1" 'BEGIN {
        split("K M G T P", u)
        i = 1
        while (v >= 1024 && i < 5) { v /= 1024; i++ }
        printf "%.0f%s", v, u[i]
    }'
}

hint() {
    local metric="$1" mount="$2"
    if [ "$metric" = "inodes" ]; then
        echo -e "    Fix: find the file-count hog — sudo du -x --inodes -d1 ${mount} | sort -rn | head -20"
        echo -e "         inodes fail writes with 'No space left on device' while bytes look fine"
    else
        echo -e "    Fix: find the space — sudo du -x -h -d1 ${mount} | sort -rh | head -20"
        echo -e "         reclaim docker  — docker system df && docker system prune -af --volumes"
    fi
}

# emit_metric <metric> <where> <free_x10> <free_human> <total_human> <mount>
emit_metric() {
    local metric="$1" where="$2" x10="$3" free_h="$4" total_h="$5" mount="$6"
    local pct label
    pct="$((x10 / 10)).$((x10 % 10))"
    printf -v label '%-6s' "$metric"
    if [ "$x10" -lt "$CRIT_X10" ]; then
        echo -e "  ${RED}[FAIL] ${label} ${where}: ${pct}% free (${free_h} of ${total_h}) — CRITICAL, under ${CRIT_FREE_PCT}%${NC}"
        hint "$metric" "$mount"
        critical=$((critical + 1))
    elif [ "$x10" -lt "$WARN_X10" ]; then
        echo -e "  ${YELLOW}[WARN] ${label} ${where}: ${pct}% free (${free_h} of ${total_h}) — under ${WARN_FREE_PCT}%${NC}"
        hint "$metric" "$mount"
        warnings=$((warnings + 1))
    else
        echo -e "  ${GREEN}[OK]${NC} ${label} ${where}: ${pct}% free (${free_h} of ${total_h})"
    fi
}

report_unknown() {
    local what="$1" reason="$2" path="$3"
    echo -e "  ${YELLOW}[UNKNOWN] ${what}: ${reason}${NC}"
    echo -e "    An unmeasurable volume is NOT a healthy volume — counted as a WARNING."
    echo -e "    Fix: run 'df -P -k ${path:-<path>}' and 'df -P -i ${path:-<path>}' by hand"
    warnings=$((warnings + 1))
}

echo "💾 Disk & Inodes:"

# The two volumes that matter: the one backing this repo, and the one backing
# the agent home.
#
# They are frequently THE SAME FILESYSTEM reached through two different mount
# points (bind mounts inside a container: /home/ywatanabe and /home/agent are
# both /dev/mapper/ubuntu--vg-ubuntu--lv here). One pool must alarm once, so
# the dedupe key is the filesystem ID from stat(2) — not the mount point,
# which bind mounts make non-unique, and not the df "Filesystem" column, which
# is shared by every independent tmpfs.
labels=("repo" "home")
paths=("$PROJECT_ROOT" "${HOME:-}")

rec_key=()
rec_label=()
rec_path=()

# Pass 1 — group the targets by filesystem, BEFORE measuring, so each pool is
# measured (and can fail) exactly once.
for ((i = 0; i < ${#paths[@]}; i++)); do
    label="${labels[$i]}"
    path="${paths[$i]}"
    if [ -z "$path" ]; then
        report_unknown "$label" "path is empty (is HOME set?)" ""
        continue
    fi
    key=$(stat -c '%d' "$path" 2> "$ERRFILE")
    if [ -z "$key" ]; then
        report_unknown "${label} (${path})" \
            "cannot identify filesystem: $(tr -d '\n' < "$ERRFILE" | cut -c1-160)" "$path"
        continue
    fi
    found=-1
    for ((j = 0; j < ${#rec_key[@]}; j++)); do
        [ "${rec_key[$j]}" = "$key" ] && found=$j && break
    done
    if [ "$found" -ge 0 ]; then
        rec_label[$found]="${rec_label[$found]}+${label}"
    else
        rec_key+=("$key")
        rec_label+=("$label")
        rec_path+=("$path")
    fi
done

# Pass 2 — measure each distinct filesystem: bytes and inodes, independently.
for ((j = 0; j < ${#rec_key[@]}; j++)); do
    rec=$(probe "${rec_path[$j]}" bytes)
    if [ "${rec%%|*}" != "OK" ]; then
        report_unknown "bytes [${rec_label[$j]}] (${rec_path[$j]})" "${rec#*|}" "${rec_path[$j]}"
        continue
    fi
    IFS='|' read -r _ src total free x10 mount <<< "$rec"
    where="${src} [${rec_label[$j]}] at ${mount}"
    emit_metric "bytes" "$where" "$x10" "$(human_kb "$free")" "$(human_kb "$total")" "$mount"

    irec=$(probe "${rec_path[$j]}" inodes)
    case "${irec%%|*}" in
        OK)
            IFS='|' read -r _ _ itotal ifree ix10 _ <<< "$irec"
            emit_metric "inodes" "$where" "$ix10" "$ifree" "$itotal" "$mount"
            ;;
        SKIP)
            echo "  [SKIP] inodes ${where}: ${irec#*|}"
            ;;
        *)
            report_unknown "inodes ${where}" "${irec#*|}" "${rec_path[$j]}"
            ;;
    esac
done

if [ "$critical" -gt 0 ]; then
    echo ""
    echo -e "  ${RED}⚠️  ${critical} metric(s) under ${CRIT_FREE_PCT}% free — writes are about to fail${NC}"
    echo -e "  ${RED}   2026-08-09: a volume in exactly this state took the a2a bus down with${NC}"
    echo -e "  ${RED}   unexplained HTTP 500s, and nothing alarmed until an unrelated task died.${NC}"
    exit 1
fi

[ "$warnings" -gt 0 ] && exit 2
exit 0
