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
# THIS CHECK MUST SURVIVE THE CONDITION IT WATCHES.
#   An earlier revision opened a `mktemp` scratch file to hold df's stderr.
#   /tmp is the SAME filesystem this check watches on every host we run on, so
#   at zero bytes free that mktemp got ENOSPC — and the alarm INVERTED: 100%
#   full reported a yellow warning instead of a red critical, printed no
#   numbers at all, and leaked raw bash errors into `make status`. A check that
#   breaks exactly when its subject breaks is worse than no check. Nothing here
#   may therefore create a file: stderr is captured into shell VARIABLES, and
#   `<<<` here-strings are avoided because bash before 5.1 materialises those
#   as temp files too (Synology DSM, the 'nas' deployment target, ships 4.x).
#
# BYTES AND INODES ARE REPORTED SEPARATELY AND ALARM INDEPENDENTLY.
#   Inode exhaustion fails writes while bytes are still plentiful, and the
#   reverse. A check that watched only bytes would have called 92% inodes
#   healthy right up to the failure. Each volume therefore gets ONE LINE PER
#   METRIC, each carrying its own severity token — including when the other
#   metric could not be measured. `df -P -k` and `df -P -i` are separate calls
#   that fail independently, so one failing never suppresses the other.
#
# NO SILENT FALLBACK.
#   During the incident `df` itself errored while measuring. A path that cannot
#   be measured is reported [UNKNOWN] and counted as a WARNING — an
#   unmeasurable volume must never read as a healthy one. Every [UNKNOWN]
#   carries the real diagnostic, never a hollow "could not check".
#
# WHICH VOLUMES ARE WATCHED
#   By default: this repo, $HOME, `/`, and Docker's data root when Docker is
#   installed (this is a Docker-only project — the volume that actually fills
#   is usually Docker's, not the repo's). Override with SCITEX_DISK_TARGETS,
#   a colon- or whitespace-separated list whose entries are `label=path` or a
#   bare `path`. Targets that turn out to share one filesystem are merged so a
#   single pool alarms once.
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

critical=0
warnings=0

# Trim an arbitrary (possibly multi-line, possibly empty) diagnostic down to
# one record-safe fragment. Never returns empty: a blank reason is the hollow
# error the repo's rules forbid.
sanitize() {
    local text="$1" out
    out=$(printf '%s' "$text" | tr '\n|' '  ' | cut -c1-160)
    # shellcheck disable=SC2001
    out=$(printf '%s' "$out" | sed 's/[[:space:]]\{1,\}$//')
    if [ -z "$out" ]; then
        printf '%s' "(command failed but printed no diagnostic)"
    else
        printf '%s' "$out"
    fi
}

# Measure one path for one metric. Emits exactly ONE record:
#   OK|<source>|<total>|<free>|<free_pct_x10>|<mount>
#   SKIP|<reason>      filesystem keeps no fixed inode table (btrfs/zfs/…)
#   UNKNOWN|<reason>   unmeasurable — the caller treats this as a WARNING
#
# stderr is captured into `out`, NOT into a temp file — see the header.
probe() {
    local path="$1" metric="$2"
    local flag out rc
    if [ "$metric" = "inodes" ]; then
        flag="-i"
    else
        flag="-k"
    fi
    out=$(df -P "$flag" "$path" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf 'UNKNOWN|df -P %s %s exited %s: %s\n' "$flag" "$path" "$rc" \
            "$(sanitize "$out")"
        return
    fi
    # Column layout is located by SHAPE, not by position. `df -P` quotes
    # nothing, so BOTH the Filesystem source and the mount point may contain
    # spaces; counting from either end alone mis-parses one of them. The
    # capacity column ("30%", or "-" where the metric does not apply) is the
    # only self-identifying field, and it is preceded by exactly three numeric
    # columns (total/used/free). Scanning from the RIGHT finds the real
    # capacity column even when a source is literally "//host/50% share".
    printf '%s\n' "$out" | awk -v metric="$metric" -v flag="$flag" -v path="$path" '
        {
            cap = 0
            for (i = NF - 1; i >= 5; i--) {
                if ($i ~ /^([0-9]+%|-)$/ &&
                    $(i - 1) ~ /^([0-9]+|-)$/ &&
                    $(i - 2) ~ /^([0-9]+|-)$/ &&
                    $(i - 3) ~ /^([0-9]+|-)$/) { cap = i; break }
            }
            if (cap == 0) next
            total = $(cap - 3)
            free = $(cap - 1)
            src = $1
            for (i = 2; i <= cap - 4; i++) src = src " " $i
            mount = $(cap + 1)
            for (i = cap + 2; i <= NF; i++) mount = mount " " $i

            # A filesystem with no fixed inode table reports "-" on some
            # kernels and a plain 0 on others (btrfs is the classic
            # 0-reporter, and the nas target is a home NAS). Both mean the
            # same thing: there is no inode budget to run out of. Treating 0
            # as UNKNOWN made this a permanent yellow line and a permanent
            # exit 2 on those hosts.
            if (metric == "inodes" && (total == "-" || total + 0 == 0)) {
                print "SKIP|" mount " keeps no fixed inode table (df reports total=" total ")"
                emitted = 1
                exit
            }
            if (total !~ /^[0-9]+$/ || free !~ /^[0-9]+$/) {
                print "UNKNOWN|df returned non-numeric " metric \
                    " (total=" total " free=" free ") for " mount
                emitted = 1
                exit
            }
            # Only bytes reach here with total == 0: a zero-byte filesystem is
            # a real anomaly, not a missing budget.
            if (total + 0 == 0) {
                print "UNKNOWN|df reports 0 total " metric " for " mount
                emitted = 1
                exit
            }
            printf "OK|%s|%s|%s|%d|%s\n", src, total, free,
                int(free * 1000 / total), mount
            emitted = 1
            exit
        }
        END {
            if (!emitted)
                print "UNKNOWN|df -P " flag " " path \
                    " printed no parsable data row"
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
    local pct label amount
    pct="$((x10 / 10)).$((x10 % 10))"
    printf -v label '%-6s' "$metric"
    # df's Available column excludes the root reserve while its size column
    # does not, so this percentage is deliberately smaller than the one implied
    # by df's own Capacity column. Say so, rather than leave an operator
    # reconciling two numbers at 3am. (Inode counts carry no reserve.)
    if [ "$metric" = "inodes" ]; then
        amount="${free_h} of ${total_h}"
    else
        amount="${free_h} available to non-root, of ${total_h} total"
    fi
    if [ "$x10" -lt "$CRIT_X10" ]; then
        echo -e "  ${RED}[FAIL] ${label} ${where}: ${pct}% free (${amount}) — CRITICAL, under ${CRIT_FREE_PCT}%${NC}"
        hint "$metric" "$mount"
        critical=$((critical + 1))
    elif [ "$x10" -lt "$WARN_X10" ]; then
        echo -e "  ${YELLOW}[WARN] ${label} ${where}: ${pct}% free (${amount}) — under ${WARN_FREE_PCT}%${NC}"
        hint "$metric" "$mount"
        warnings=$((warnings + 1))
    else
        echo -e "  ${GREEN}[OK]${NC} ${label} ${where}: ${pct}% free (${amount})"
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

# ── Which volumes to watch ─────────────────────────────────
labels=()
paths=()
notes=()

if [ -n "${SCITEX_DISK_TARGETS:-}" ]; then
    # Colon- or whitespace-separated. Entries are `label=path` or a bare
    # `path` (which then labels itself). Paths containing spaces cannot be
    # expressed here by design — the separator set is the PATH convention.
    _saved_ifs="$IFS"
    IFS=$': \t\n'
    for entry in ${SCITEX_DISK_TARGETS}; do
        [ -z "$entry" ] && continue
        if [[ "$entry" == *=* ]]; then
            labels+=("${entry%%=*}")
            paths+=("${entry#*=}")
        else
            labels+=("$entry")
            paths+=("$entry")
        fi
    done
    IFS="$_saved_ifs"
    if [ "${#paths[@]}" -eq 0 ]; then
        report_unknown "targets" \
            "SCITEX_DISK_TARGETS is set but names no paths" ""
    fi
else
    # The repo, the agent home, the root filesystem, and — because this is a
    # Docker-only project — Docker's data root, which is where Postgres and
    # the OpenAlex volumes actually live. Watching only the repo would have
    # printed [OK] through the exact incident this file exists for whenever
    # Docker's storage sits on another volume.
    labels=("repo" "home" "root")
    paths=("$PROJECT_ROOT" "${HOME:-}" "/")

    docker_root=""
    if command -v docker > /dev/null 2>&1; then
        if command -v timeout > /dev/null 2>&1; then
            docker_root=$(timeout 5 docker info --format '{{.DockerRootDir}}' 2> /dev/null)
        else
            docker_root=$(docker info --format '{{.DockerRootDir}}' 2> /dev/null)
        fi
        docker_root="${docker_root%%$'\n'*}"
        if [ -n "$docker_root" ] && [ -d "$docker_root" ]; then
            labels+=("docker")
            paths+=("$docker_root")
        else
            notes+=("docker is installed but its data root could not be resolved ('docker info' gave no usable DockerRootDir) — Docker's volume is not measured below")
        fi
    else
        notes+=("docker is not installed here, so there is no Docker data root to measure")
    fi
fi

for note in ${notes[@]+"${notes[@]}"}; do
    echo -e "  ${BLUE}note:${NC} ${note}"
done

rec_key=()
rec_label=()
rec_path=()

# Pass 1 — group the targets by filesystem, BEFORE measuring, so each pool is
# measured (and can fail) exactly once.
#
# The dedupe key is stat(2)'s filesystem id. This is a HEURISTIC, not a
# definition: it is right about the case that actually bites us — one pool
# reached through several mount points (bind mounts inside a container put
# /home/ywatanabe and /home/agent on one device) — where the mount point is
# non-unique and df's "Filesystem" column is shared by every independent
# tmpfs. It is known to OVER-SPLIT: measured on this host, `/` and `/tmp`
# report byte-identical df figures from the same pool yet carry st_dev 106 vs
# 64512, because fuse-overlayfs passes through to the underlying device. An
# over-split costs a duplicate line; an under-split would hide a volume, so
# this is the safe direction to be wrong in.
for ((i = 0; i < ${#paths[@]}; i++)); do
    label="${labels[$i]}"
    path="${paths[$i]}"
    if [ -z "$path" ]; then
        report_unknown "$label" "path is empty (is HOME set?)" ""
        continue
    fi
    # stderr into a VARIABLE, not a temp file: at 0 bytes free the temp file
    # is exactly what fails, and it took the reason string with it.
    key=$(stat -c '%d' "$path" 2>&1)
    if [ -z "$key" ] || [ -n "${key//[0-9]/}" ]; then
        report_unknown "${label} (${path})" \
            "cannot identify filesystem: $(sanitize "$key")" "$path"
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
# A failed bytes probe must NOT skip the inode probe: the header promises one
# line per metric, and a reader who sees a single [UNKNOWN] for bytes would
# otherwise conclude inodes are fine.
for ((j = 0; j < ${#rec_key[@]}; j++)); do
    where="[${rec_label[$j]}] (${rec_path[$j]})"
    mount_for_hint="${rec_path[$j]}"

    rec=$(probe "${rec_path[$j]}" bytes)
    if [ "${rec%%|*}" = "OK" ]; then
        IFS='|' read -r _ src total free x10 mount < <(printf '%s\n' "$rec")
        where="${src} [${rec_label[$j]}] at ${mount}"
        mount_for_hint="$mount"
        emit_metric "bytes" "$where" "$x10" "$(human_kb "$free")" \
            "$(human_kb "$total")" "$mount"
    else
        report_unknown "bytes ${where}" "${rec#*|}" "${rec_path[$j]}"
    fi

    irec=$(probe "${rec_path[$j]}" inodes)
    case "${irec%%|*}" in
        OK)
            IFS='|' read -r _ _ itotal ifree ix10 imount < <(printf '%s\n' "$irec")
            emit_metric "inodes" "$where" "$ix10" "$ifree" "$itotal" \
                "${imount:-$mount_for_hint}"
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
