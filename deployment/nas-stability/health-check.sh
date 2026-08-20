#!/usr/bin/env bash
# health-check.sh -- Watchdog for scitex.ai with tiered escalation
# Designed to run every 5 minutes from WSL cron:
#   */5 * * * * /path/to/health-check.sh >> /tmp/nas-health-check.log 2>&1
set -euo pipefail

# --- Configuration ---
SITE_URL="https://scitex.ai"
CURL_TIMEOUT=15
# Try LAN-direct first: the bastion route (`nas`) rides the same Cloudflare
# tunnel this script guards, so it is dead exactly when we need SSH most
# (incident 2026-07-06: tunnel down -> `ssh nas` down with it).
SSH_HOSTS="${NAS_SSH_HOSTS:-nas-direct nas}"
SSH_TIMEOUT=10
STATE_FILE="/tmp/nas-health-check.state"
# Boot grace: django boot (migrations + visitor pool + app installs) can take
# ~8-10 min on the loaded NAS; restarting mid-boot creates a restart loop
# (incident 2026-07-07). Cooldown: never blanket-restart twice in a row fast.
BOOT_GRACE_SECONDS="${NAS_BOOT_GRACE_SECONDS:-720}"
RESTART_COOLDOWN_SECONDS="${NAS_RESTART_COOLDOWN_SECONDS:-1800}"
# Notification commands (scitex notification system).
# Cron runs with a minimal PATH (/usr/bin:/bin) and scitex lives in a venv —
# resolve it absolutely or every alert fails silently. Incident 2026-07-06:
# 106 consecutive detected failures, zero notifications delivered, because
# bare `scitex` was not on cron's PATH.
SCITEX_BIN="${SCITEX_BIN:-$(command -v scitex || echo "$HOME/.env-3.11/bin/scitex")}"
NOTIFY_TELEGRAM="$SCITEX_BIN notification send"
# `sms` was RENAMED to `send-sms`. The old name still exists as a shim that
# exits 2 with "was renamed to ... Re-run with: scitex-notification send-sms"
# and forwards NOTHING — so every Tier 3 SMS since the rename has failed.
# Measured 2026-08-04 during a real outage: two consecutive Tier 3 escalations,
# both logging only "WARNING: SMS notification failed" because the shim's
# explanation was being sent to /dev/null.
NOTIFY_SMS="$SCITEX_BIN notification send-sms"
NOTIFY_CALL="$SCITEX_BIN notification call"

# TWILIO CREDENTIALS MUST BE LOADED EXPLICITLY.
#
# `send-sms` and `call` read SCITEX_NOTIFICATION_TWILIO_{SID,TOKEN,FROM,TO} from
# the ENVIRONMENT, and there is no ~/.scitex/notification/config.yaml to fall
# back on. Those vars are defined in ~/.bash.d/secrets/, which is sourced by an
# INTERACTIVE LOGIN shell — and cron gives us neither. So in cron they are unset
# and both phone rungs fail, while the same commands work perfectly when a human
# tests them from a terminal. That divergence is why this went unnoticed.
#
# This is the SAME failure class as the SCITEX_BIN line above (incident
# 2026-07-06: cron's minimal PATH). That fix made the BINARY cron-safe and left
# the CREDENTIALS behind — the lesson was written down directly above the line
# that reintroduced it in another form.
for _secret_file in \
    "$HOME/.bash.d/secrets/000_ENV/api_keys/40_notification_twilio.src" \
    "$HOME/.bash.d/secrets/010_scitex/01_notification.src"; do
    # shellcheck disable=SC1090
    [ -r "$_secret_file" ] && source "$_secret_file"
done
# Report MISSING credentials by name (never values) rather than discovering it
# mid-incident. Absence is stated here so a broken alarm is visible in the log
# on every ordinary run, not only on the night it is needed.
MISSING_TWILIO=""
for _v in SCITEX_NOTIFICATION_TWILIO_SID SCITEX_NOTIFICATION_TWILIO_TOKEN \
    SCITEX_NOTIFICATION_TWILIO_FROM SCITEX_NOTIFICATION_TWILIO_TO; do
    [ -z "${!_v:-}" ] && MISSING_TWILIO="$MISSING_TWILIO $_v"
done

SSH_OPTS=(-o ConnectTimeout="$SSH_TIMEOUT" -o BatchMode=yes
    -o ControlMaster=no -o ControlPath=none -o ForwardX11=no)

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log() {
    echo "[$(timestamp)] $*"
}

get_failure_count() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "0"
    fi
}

set_failure_count() {
    echo "$1" >"$STATE_FILE"
}

site_up() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$CURL_TIMEOUT" --max-time "$((CURL_TIMEOUT * 2))" "$SITE_URL" 2>/dev/null || echo "000")
    HTTP_CODE="$code"
    [ "$code" -ge 200 ] && [ "$code" -lt 400 ]
}

pick_ssh_host() {
    local host
    for host in $SSH_HOSTS; do
        if ssh "${SSH_OPTS[@]}" "$host" "echo ok" >/dev/null 2>&1; then
            echo "$host"
            return 0
        fi
    done
    return 1
}

# --- Step 0: `--check-alarm` -- prove the escalation path works, on demand ---
#
# WHY THIS EXISTS: before this flag, the ONLY thing that exercised Tier 3 was a
# real outage — so the alarm was tested exactly when it was needed and never
# before. It had been broken for an unknown length of time and was discovered
# mid-incident on 2026-08-04, with both rungs failing.
#
# It is a CONJUNCTION of two independent checks, and it has to be, because
# neither is sufficient alone:
#
#   1. credentials present  — all four Twilio vars are non-empty
#   2. verb resolves        — the command runs under --dry-run
#
# --dry-run DOES NOT VALIDATE CREDENTIALS. Measured 2026-08-05: with all four
# vars deliberately unset, both `send-sms --dry-run` and `call --dry-run` still
# exited 0. So a passing dry-run means "this verb exists and parses", nothing
# more — reading it as "the channel works" is exactly the false green this flag
# exists to prevent. Check 1 is what actually catches the cron-environment bug.
#
# Neither channel sends anything, which is what makes this safe to run from cron
# at any hour without ringing a phone at 03:00.
#
# Exit 0 = the alarm would fire. Exit 1 = it would not, and the reason is named.
if [ "${1:-}" = "--check-alarm" ]; then
    rc=0
    if [ -n "$MISSING_TWILIO" ]; then
        log "ALARM CHECK: FAIL — missing credentials:${MISSING_TWILIO}"
        rc=1
    else
        log "ALARM CHECK: credentials present (4/4)"
    fi
    for channel in "SMS:${NOTIFY_SMS}" "CALL:${NOTIFY_CALL}"; do
        name="${channel%%:*}"
        cmd="${channel#*:}"
        if out=$(${cmd} "alarm self-check (dry run) — not a real alert" --dry-run 2>&1); then
            # Deliberately NOT worded "OK": this proves the verb resolves, and
            # says nothing about whether the message would reach anyone.
            log "ALARM CHECK: ${name} verb resolves (dry-run; credentials NOT tested here)"
        else
            log "ALARM CHECK: ${name} FAIL — ${out}"
            rc=1
        fi
    done
    [ "$rc" -eq 0 ] && log "ALARM CHECK: PASS — Tier 3 would fire" \
        || log "ALARM CHECK: FAIL — Tier 3 would NOT reach anyone"
    exit "$rc"
fi

# --- Step 1: Check if site is reachable ---
log "Checking ${SITE_URL}..."

if site_up; then
    log "OK: ${SITE_URL} returned HTTP ${HTTP_CODE}"
    set_failure_count 0
    exit 0
fi

log "FAIL: ${SITE_URL} returned HTTP ${HTTP_CODE}"
FAILURES=$(get_failure_count)
FAILURES=$((FAILURES + 1))
set_failure_count "$FAILURES"

# --- Step 2 (Tier 1): SSH self-heal ---
log "Tier 1: Attempting SSH recovery (failure count: ${FAILURES})..."

if SSH_HOST=$(pick_ssh_host); then
    log "Tier 1: NAS reachable via '${SSH_HOST}'"

    # 1a: start EXITED **and CREATED** prod containers. A manually-stopped
    # container (e.g. cloudflared, incident 2026-07-06) has restart:always
    # disabled and is invisible to `docker restart $(docker ps -q)`.
    #
    # `created` is a DISTINCT docker state, not a kind of `exited`: a container
    # that was created but never started has no exit code and never appears
    # under status=exited. Filtering on exited alone therefore skipped them at
    # EVERY recovery tier. That is how 7 prod containers stayed dark after the
    # host reboot on 2026-07-24 while this script reported nothing to do —
    # invisible to the healer, and to anyone reading its log.
    # Multiple --filter status= values are OR'd by docker, so this widens the
    # set without disturbing the exited path.
    STARTED=$(ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
        "docker ps -a --filter status=exited --filter status=created --filter name=scitex-hub-prod --format '{{.Names}}' | xargs -r docker start" 2>/dev/null || true)
    if [ -n "$STARTED" ]; then
        log "Tier 1a: Started stopped/created prod container(s): ${STARTED}. Waiting 30s..."
        sleep 30
        if site_up; then
            log "Tier 1a: RECOVERED. Site is back (HTTP ${HTTP_CODE})"
            set_failure_count 0
            ${NOTIFY_TELEGRAM} "NAS auto-recovered: started stopped container(s) ${STARTED}. Site is back." 2>/dev/null || true
            exit 0
        fi
        log "Tier 1a: Starting stopped containers did not fix the issue (HTTP ${HTTP_CODE})"
    else
        log "Tier 1a: No exited prod containers to start"
    fi

    # 1b: restart running containers (original blanket recovery).
    #
    # BOOT-GRACE GUARD (incident 2026-07-07): django's boot (migrations +
    # visitor pool + workspace-app pip installs) takes LONGER than the
    # 5-minute cron interval. Restarting while containers are still
    # booting guarantees the next check also fails -> restart loop that
    # kept prod down for ~90 min. Skip 1b while any prod container is
    # younger than BOOT_GRACE_SECONDS, and never restart twice within
    # RESTART_COOLDOWN_SECONDS.
    YOUNGEST_AGE=$(ssh "${SSH_OPTS[@]}" "$SSH_HOST" '
        now=$(date +%s); min=999999
        for id in $(docker ps -q --filter name=scitex-hub-prod); do
            started=$(docker inspect -f "{{.State.StartedAt}}" "$id")
            age=$((now - $(date -d "$started" +%s)))
            [ "$age" -lt "$min" ] && min=$age
        done
        echo "$min"' 2>/dev/null || echo 999999)
    LAST_RESTART_FILE="/tmp/nas-health-check.last-restart"
    LAST_RESTART=$(cat "$LAST_RESTART_FILE" 2>/dev/null || echo 0)
    SINCE_RESTART=$(($(date +%s) - LAST_RESTART))
    if [ "$YOUNGEST_AGE" -lt "$BOOT_GRACE_SECONDS" ]; then
        log "Tier 1b: SKIPPED — containers still booting (youngest ${YOUNGEST_AGE}s < grace ${BOOT_GRACE_SECONDS}s)"
    elif [ "$SINCE_RESTART" -lt "$RESTART_COOLDOWN_SECONDS" ]; then
        log "Tier 1b: SKIPPED — last restart ${SINCE_RESTART}s ago (< cooldown ${RESTART_COOLDOWN_SECONDS}s)"
    elif ssh "${SSH_OPTS[@]}" "$SSH_HOST" "docker restart \$(docker ps -q)" >/dev/null 2>&1; then
        date +%s >"$LAST_RESTART_FILE"
        log "Tier 1b: Docker containers restarted via SSH. Waiting 30s for services..."
        sleep 30
        if site_up; then
            log "Tier 1b: RECOVERED. Site is back (HTTP ${HTTP_CODE})"
            set_failure_count 0
            ${NOTIFY_TELEGRAM} "NAS auto-recovered. Site was down, Docker containers restarted automatically." 2>/dev/null || true
            exit 0
        fi
        log "Tier 1b: Docker restart did not fix the issue (HTTP ${HTTP_CODE})"
    fi
else
    log "Tier 1: NAS unreachable on all SSH routes (${SSH_HOSTS})"
fi

# --- Step 3 (Tier 2): SSH failed or restart did not help -- Telegram ---
log "Tier 2: Sending Telegram alert..."
${NOTIFY_TELEGRAM} "ALERT: scitex.ai is DOWN (HTTP ${HTTP_CODE}). Auto-recovery failed. SSH may be unreachable. Failure count: ${FAILURES}" 2>/dev/null || {
    log "WARNING: Telegram notification failed"
}

# --- Step 4 (Tier 3): Persistent failure -- Phone + SMS ---
if [ "$FAILURES" -ge 3 ]; then
    log "Tier 3: Persistent failure (${FAILURES} consecutive). Sending SMS + phone call..."

    # NEVER `2>/dev/null` HERE. The previous version discarded stderr and logged
    # a bare "WARNING: SMS notification failed" — while the discarded stderr
    # said, in full, "was renamed to send-sms. Re-run with: ... send-sms".
    # The fix was in the output the failure handler was throwing away.
    if [ -n "$MISSING_TWILIO" ]; then
        log "ERROR: Tier 3 CANNOT alert — missing credentials:${MISSING_TWILIO}"
        log "ERROR:   cron does not source ~/.bash.d/secrets; see the loader at the top of this script"
    fi

    if out=$(${NOTIFY_SMS} "CRITICAL: scitex.ai down for ${FAILURES} checks (~$((FAILURES * 5)) min). NAS may need physical restart." 2>&1); then
        log "Tier 3: SMS sent"
    else
        log "ERROR: SMS notification FAILED (exit $?): ${out}"
    fi

    if out=$(${NOTIFY_CALL} "scitex.ai has been unreachable for $((FAILURES * 5)) minutes. NAS may need a physical restart." 2>&1); then
        log "Tier 3: phone call placed"
    else
        log "ERROR: phone call notification FAILED (exit $?): ${out}"
    fi
fi

log "Health check complete. Failures: ${FAILURES}"
exit 1
