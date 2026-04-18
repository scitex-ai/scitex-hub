#!/usr/bin/env bash
# observe.sh -- Per-minute read-only observation sampler for scitex.ai
#
# Background: 2026-04-18 site-wide 504 outage (issue #147). First guess
# blamed cgroup memory limit; cgroup PSI + oom_kill=0 disproved it.
# We need time-series data to identify the real trigger before the next fix.
#
# Run on the NAS (where docker + nginx + cgroups live), one sample/minute:
#   * * * * * /home/ywatanabe/proj/scitex-cloud/deployment/nas-stability/observe.sh
#
# Appends TSV rows to ~/proj/scitex-cloud/logs/obs/YYYY-MM-DD.tsv
# Pure observation: no restarts, no writes outside logs/obs/.

set -u

CONTAINER_FILTER="scitex-cloud-prod"
DJANGO="scitex-cloud-prod-django-1"
NGINX="scitex-cloud-prod-nginx-1"
LOG_ROOT="${HOME}/proj/scitex-cloud/logs/obs"
DAY_FILE="${LOG_ROOT}/$(date -u +%Y-%m-%d).tsv"

mkdir -p "${LOG_ROOT}"

if [ ! -s "${DAY_FILE}" ]; then
    printf 'ts_utc\tcontainer\tcpu_pct\tmem_mib\tmem_anon_mib\tmem_file_mib\tcg_events_max\tmem_psi_some_us\tmem_psi_full_us\tcpu_psi_some_us\tthreads\test_conns\tnginx_req_1m\tnginx_5xx_1m\tnginx_504_1m\tnginx_499_1m\n' >>"${DAY_FILE}"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Helper: extract total=N from a PSI line matching prefix (some|full)
psi_total() {
    local file="$1" prefix="$2"
    awk -v p="${prefix}" '$1==p { for (i=1;i<=NF;i++) if ($i ~ /^total=/) { sub("total=","",$i); print $i; exit } }' "${file}" 2>/dev/null
}

# ---- per-container metrics ----
stats_raw="$(docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null |
    awk -F'\t' -v f="${CONTAINER_FILTER}" '$1 ~ f')"

while IFS=$'\t' read -r name cpu memu; do
    [ -z "${name}" ] && continue
    cpu_pct="${cpu%\%}"
    mem_raw="$(echo "${memu}" | awk '{print $1}')"
    mem_mib="$(echo "${mem_raw}" | awk '
        /GiB$/ { sub("GiB",""); printf "%.1f", $0 * 1024; exit }
        /MiB$/ { sub("MiB",""); printf "%.1f", $0; exit }
        /KiB$/ { sub("KiB",""); printf "%.3f", $0 / 1024; exit }
        /B$/   { sub("B","");   printf "%.3f", $0 / 1048576; exit }
    ')"

    anon_mib=""
    file_mib=""
    events_max=""
    mem_some=""
    mem_full=""
    cpu_some=""
    threads=""
    est_conns=""
    if [ "${name}" = "${DJANGO}" ]; then
        cid="$(docker inspect --format '{{.Id}}' "${name}" 2>/dev/null)"
        cg="/sys/fs/cgroup/system.slice/docker-${cid}.scope"
        if [ -d "${cg}" ]; then
            anon="$(awk '$1=="anon"{print $2; exit}' "${cg}/memory.stat" 2>/dev/null)"
            file="$(awk '$1=="file"{print $2; exit}' "${cg}/memory.stat" 2>/dev/null)"
            anon_mib="$(awk -v v="${anon:-0}" 'BEGIN{printf "%.1f", v/1048576}')"
            file_mib="$(awk -v v="${file:-0}" 'BEGIN{printf "%.1f", v/1048576}')"
            events_max="$(awk '$1=="max"{print $2; exit}' "${cg}/memory.events" 2>/dev/null)"
            mem_some="$(psi_total "${cg}/memory.pressure" some)"
            mem_full="$(psi_total "${cg}/memory.pressure" full)"
            cpu_some="$(psi_total "${cg}/cpu.pressure" some)"
        fi
        threads="$(timeout 5 docker exec "${name}" ls /proc/1/task 2>/dev/null | wc -l)"
        # TCP state 01 = ESTABLISHED
        # shellcheck disable=SC2016
        est_conns="$(timeout 5 docker exec "${name}" awk 'NR>1 && $4=="01" {c++} END{print c+0}' /proc/1/net/tcp 2>/dev/null)"
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t\t\t\n' \
        "${ts}" "${name}" "${cpu_pct:-}" "${mem_mib:-}" \
        "${anon_mib}" "${file_mib}" "${events_max}" \
        "${mem_some}" "${mem_full}" "${cpu_some}" \
        "${threads}" "${est_conns}" \
        >>"${DAY_FILE}"
done <<<"${stats_raw}"

# ---- nginx request/error counts for the last minute ----
# Parse inside the nginx container. Match this-minute or prev-minute key.
now_key="$(date -u +'%d/%b/%Y:%H:%M')"
prev_key="$(date -u -d '1 minute ago' +'%d/%b/%Y:%H:%M')"
nginx_counts="$(timeout 10 docker logs --tail 20000 "${NGINX}" 2>/dev/null |
    awk -v a="${prev_key}" -v b="${now_key}" '
        {
            s=index($0,"[")+1
            e=index($0,"]")
            if (s<2||e<=s) next
            key=substr($0, s, 17)  # "18/Apr/2026:14:15"
            if (key!=a && key!=b) next
            total++
            st=$9
            if (st ~ /^5/) s5++
            if (st == "504") s504++
            if (st == "499") s499++
        }
        END { printf "%d\t%d\t%d\t%d\n", total+0, s5+0, s504+0, s499+0 }
    ')"

req1m="$(echo "${nginx_counts}" | awk -F'\t' '{print $1+0}')"
s5xx1m="$(echo "${nginx_counts}" | awk -F'\t' '{print $2+0}')"
s5041m="$(echo "${nginx_counts}" | awk -F'\t' '{print $3+0}')"
s4991m="$(echo "${nginx_counts}" | awk -F'\t' '{print $4+0}')"

printf '%s\t_nginx\t\t\t\t\t\t\t\t\t\t\t%s\t%s\t%s\t%s\n' \
    "${ts}" "${req1m}" "${s5xx1m}" "${s5041m}" "${s4991m}" \
    >>"${DAY_FILE}"

# ---- capture daphne stack when 504 rate is high ----
# When 504_1m >= 3, dump py-spy stacks so we have a stack trace aligned
# with the outage signature. Rate-limited to once per 5 minutes to avoid
# spamming. Output goes to logs/obs/stacks/ with the TS in the filename.
STACK_DIR="${LOG_ROOT}/stacks"
STACK_THRESHOLD=3
STACK_COOLDOWN=300
mkdir -p "${STACK_DIR}"
last_stack_ts_file="${STACK_DIR}/.last_ts"
now_epoch="$(date -u +%s)"
last_stack_epoch=0
[ -f "${last_stack_ts_file}" ] && last_stack_epoch="$(cat "${last_stack_ts_file}" 2>/dev/null)"
elapsed=$((now_epoch - last_stack_epoch))

if [ "${s5041m:-0}" -ge "${STACK_THRESHOLD}" ] && [ "${elapsed}" -ge "${STACK_COOLDOWN}" ]; then
    echo "${now_epoch}" >"${last_stack_ts_file}"
    stack_file="${STACK_DIR}/${ts}_504-${s5041m}.txt"
    # py-spy is already installed inside the django container.
    {
        printf '# %s  504_1m=%s  req_1m=%s  est_conns=%s  threads=%s\n' \
            "${ts}" "${s5041m}" "${req1m}" "${est_conns}" "${threads}"
        docker exec --user root --privileged "${DJANGO}" \
            py-spy dump --pid 1 2>&1
    } >"${stack_file}"
fi

exit 0
