#!/bin/bash
# SLURM accounting health check — FAILS LOUDLY (exit 1) when jobs would not be metered.
#
# Why: from 2026-10-02 to 2026-11-26 slurmctld + slurmdbd on the SciTeX cluster
# were `failed` after a boot race, and every existing check still exited 0. sacct
# recorded 0 jobs for 8 weeks and nobody was told. Usage metering and billing
# read sacct, so "accounting is down" must be an error, not a warning.
#
# Checks (each prints [OK] or [FAIL]; any FAIL -> exit 1 and a daemon.crit log):
#   - on the accounting host (slurmdbd unit present): mariadb, slurmdbd, slurmctld active
#   - the controller answers (scontrol ping)
#   - effective config: AccountingStorageType=accounting_storage/slurmdbd,
#     JobAcctGatherType=jobacct_gather/cgroup, AccountingStoreFlags has job_comment,
#     TrackWCKey=Yes, and gres/gpu in AccountingStorageTRES when the cluster has GPUs
#   - slurmdbd answers (sacctmgr show cluster lists ClusterName)
#   - sacct can query the last day
#   - the controller's DBD agent queue is not backing up (records not reaching the DB)
#
# Reads no secrets: slurm.conf holds none, slurmdbd.conf (which does) is never read.
#
# Usage: check-slurm-accounting.sh [--quiet]     (run on any cluster node)
# Exit:  0 healthy, 1 accounting broken.

set -uo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1
T="timeout 15"
DBD_QUEUE_MAX=${SCITEX_SLURM_DBD_QUEUE_MAX:-500}

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
[ -t 1 ] || { RED=''; GREEN=''; NC=''; }

failures=()
ok()   { [ "$QUIET" -eq 1 ] || echo -e "  ${GREEN}[OK]${NC} $*"; }
fail() { failures+=("$*"); echo -e "  ${RED}[FAIL] $*${NC}"; }

[ "$QUIET" -eq 1 ] || echo "SLURM accounting:"

if ! command -v sacct >/dev/null 2>&1; then
    fail "sacct not installed on $(hostname)"
else
    if systemctl cat slurmdbd.service >/dev/null 2>&1; then
        for unit in mariadb slurmdbd slurmctld; do
            if systemctl is-active --quiet "$unit"; then ok "$unit active"
            else fail "$unit is $(systemctl is-active "$unit" 2>&1) on $(hostname)"; fi
        done
    fi

    if $T scontrol ping 2>/dev/null | grep -q 'is UP'; then ok "controller UP"
    else fail "controller does not answer (scontrol ping)"; fi

    cfg=$($T scontrol show config 2>/dev/null)
    get() { awk -F' = ' -v k="$1" '$1 ~ "^"k" *$" {print $2; exit}' <<<"$cfg"; }
    if [ -z "$cfg" ]; then
        fail "cannot read the effective SLURM config (scontrol show config)"
    else
        cluster=$(get ClusterName)
        [ "$(get AccountingStorageType)" = "accounting_storage/slurmdbd" ] \
            && ok "AccountingStorageType=slurmdbd" \
            || fail "AccountingStorageType is '$(get AccountingStorageType)', expected accounting_storage/slurmdbd"
        [ "$(get JobAcctGatherType)" = "jobacct_gather/cgroup" ] \
            && ok "JobAcctGatherType=cgroup" \
            || fail "JobAcctGatherType is '$(get JobAcctGatherType)', expected jobacct_gather/cgroup"
        grep -q 'job_comment' <<<"$(get AccountingStoreFlags)" \
            && ok "AccountingStoreFlags has job_comment" \
            || fail "AccountingStoreFlags lacks job_comment: sacct would drop --comment (the project tag)"
        [ "$(get TrackWCKey)" = "Yes" ] \
            && ok "TrackWCKey=Yes" \
            || fail "TrackWCKey is '$(get TrackWCKey)': sacct would drop --wckey"
        if $T sinfo -h -o '%G' 2>/dev/null | grep -q 'gpu'; then
            grep -q 'gres/gpu' <<<"$(get AccountingStorageTRES)" \
                && ok "AccountingStorageTRES has gres/gpu" \
                || fail "cluster has GPUs but AccountingStorageTRES lacks gres/gpu: GPU time unmetered"
        fi

        if [ -n "$cluster" ] && $T sacctmgr -n -P show cluster format=Cluster 2>/dev/null | grep -qx "$cluster"; then
            ok "slurmdbd answers (cluster '$cluster' registered)"
        else
            fail "slurmdbd does not answer or cluster '$cluster' is not registered (sacctmgr show cluster)"
        fi
    fi

    if $T sacct -a -X -n -S now-1days -o JobID >/dev/null 2>&1; then ok "sacct query works"
    else fail "sacct cannot query the accounting database"; fi

    q=$($T sdiag 2>/dev/null | awk -F: '/DBD Agent queue size/ {gsub(/ /,"",$2); print $2; exit}')
    if [ -n "$q" ] && [ "$q" -gt "$DBD_QUEUE_MAX" ] 2>/dev/null; then
        fail "DBD agent queue is $q (> $DBD_QUEUE_MAX): job records are not reaching slurmdbd"
    elif [ -n "$q" ]; then ok "DBD agent queue $q"; fi
fi

if [ "${#failures[@]}" -gt 0 ]; then
    msg="SLURM ACCOUNTING BROKEN on $(hostname): $(IFS=';'; echo "${failures[*]}")"
    echo -e "${RED}${msg}${NC}" >&2
    logger -t scitex-slurm-accounting -p daemon.crit "$msg" 2>/dev/null
    exit 1
fi
[ "$QUIET" -eq 1 ] || echo -e "  ${GREEN}SLURM accounting healthy${NC}"
exit 0
