#!/usr/bin/env bash
# health-check.sh -- Watchdog for scitex.ai with tiered escalation
# Designed to run every 5 minutes from WSL cron:
#   */5 * * * * /path/to/health-check.sh >> /tmp/nas-health-check.log 2>&1
set -euo pipefail

# --- Configuration ---
SITE_URL="https://scitex.ai"
CURL_TIMEOUT=15
SSH_HOST="nas"
SSH_TIMEOUT=10
STATE_FILE="/tmp/nas-health-check.state"
# Notification commands (scitex notification system)
NOTIFY_TELEGRAM="scitex notification send"
NOTIFY_SMS="scitex notification sms"
NOTIFY_CALL="scitex notification call"

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

# --- Step 1: Check if site is reachable ---
log "Checking ${SITE_URL}..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$CURL_TIMEOUT" --max-time "$((CURL_TIMEOUT * 2))" "$SITE_URL" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
    log "OK: ${SITE_URL} returned HTTP ${HTTP_CODE}"
    set_failure_count 0
    exit 0
fi

log "FAIL: ${SITE_URL} returned HTTP ${HTTP_CODE}"
FAILURES=$(get_failure_count)
FAILURES=$((FAILURES + 1))
set_failure_count "$FAILURES"

# --- Step 2 (Tier 1): Try SSH + Docker restart ---
log "Tier 1: Attempting SSH recovery (failure count: ${FAILURES})..."

if ssh -o ConnectTimeout="$SSH_TIMEOUT" -o BatchMode=yes "$SSH_HOST" "docker restart \$(docker ps -q)" 2>/dev/null; then
    log "Tier 1: Docker containers restarted via SSH. Waiting 30s for services..."
    sleep 30

    # Verify recovery
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$CURL_TIMEOUT" --max-time "$((CURL_TIMEOUT * 2))" "$SITE_URL" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
        log "Tier 1: RECOVERED. Site is back (HTTP ${HTTP_CODE})"
        set_failure_count 0

        # Still notify about the incident
        ${NOTIFY_TELEGRAM} "NAS auto-recovered. Site was down, Docker containers restarted automatically." 2>/dev/null || true
        exit 0
    fi
    log "Tier 1: Docker restart did not fix the issue (HTTP ${HTTP_CODE})"
fi

# --- Step 3 (Tier 2): SSH failed or restart did not help -- Telegram ---
log "Tier 2: Sending Telegram alert..."
${NOTIFY_TELEGRAM} "ALERT: scitex.ai is DOWN (HTTP ${HTTP_CODE}). Auto-recovery failed. SSH may be unreachable. Failure count: ${FAILURES}" 2>/dev/null || {
    log "WARNING: Telegram notification failed"
}

# --- Step 4 (Tier 3): Persistent failure -- Phone + SMS ---
if [ "$FAILURES" -ge 3 ]; then
    log "Tier 3: Persistent failure (${FAILURES} consecutive). Sending SMS + phone call..."

    ${NOTIFY_SMS} "CRITICAL: scitex.ai down for ${FAILURES} checks (~$((FAILURES * 5)) min). NAS may need physical restart." 2>/dev/null || {
        log "WARNING: SMS notification failed"
    }

    ${NOTIFY_CALL} "scitex.ai has been unreachable for $((FAILURES * 5)) minutes. NAS may need a physical restart." 2>/dev/null || {
        log "WARNING: Phone call notification failed"
    }
fi

log "Health check complete. Failures: ${FAILURES}"
exit 1
