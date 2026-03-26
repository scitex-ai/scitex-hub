#!/usr/bin/env bash
# diagnose.sh -- Post-incident diagnostics for the NAS
# Run on the NAS after a reboot or outage
set -euo pipefail

REPORT_FILE="/tmp/nas-diagnosis-$(date +%Y%m%d-%H%M%S).txt"

section() {
    echo ""
    echo "========================================"
    echo " $1"
    echo "========================================"
    echo ""
}

{
    echo "NAS Diagnostic Report"
    echo "Generated: $(date)"
    echo "Hostname:  $(hostname)"
    echo "Uptime:    $(uptime)"

    # --- OOM Events ---
    section "OOM Killer Events (dmesg)"
    dmesg | grep -i "oom\|killed process\|out of memory" 2>/dev/null || echo "(none found)"

    # --- Previous Boot Errors ---
    section "Previous Boot Errors (journalctl -b -1)"
    journalctl -b -1 --priority=err --no-pager 2>/dev/null | tail -50 || echo "(previous boot journal not available)"

    # --- Current Boot Errors ---
    section "Current Boot Errors (journalctl -b 0)"
    journalctl -b 0 --priority=err --no-pager 2>/dev/null | tail -30 || echo "(no errors)"

    # --- Docker Status ---
    section "Docker Container Status"
    if command -v docker &>/dev/null; then
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "(docker not accessible)"
    else
        echo "(docker not installed)"
    fi

    # --- Docker Resource Usage ---
    section "Docker Resource Usage"
    if command -v docker &>/dev/null; then
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" 2>/dev/null || echo "(docker not accessible)"
    fi

    # --- Memory ---
    section "Memory Usage"
    free -h 2>/dev/null || echo "(free not available)"

    # --- Disk Space ---
    section "Disk Space"
    df -h 2>/dev/null || echo "(df not available)"

    # --- Disk I/O ---
    section "Disk I/O (if iostat available)"
    iostat -x 1 1 2>/dev/null || echo "(iostat not available -- install sysstat)"

    # --- Top Processes by Memory ---
    section "Top 15 Processes by Memory"
    ps aux --sort=-%mem 2>/dev/null | head -16 || echo "(ps not available)"

    # --- sshd OOM Protection ---
    section "sshd OOM Protection Status"
    SSHD_PID=$(pgrep -o sshd 2>/dev/null || echo "")
    if [ -n "$SSHD_PID" ]; then
        SCORE=$(cat "/proc/${SSHD_PID}/oom_score_adj" 2>/dev/null || echo "UNKNOWN")
        echo "sshd PID: ${SSHD_PID}"
        echo "OOM score adjust: ${SCORE}"
        if [ "$SCORE" = "-1000" ]; then
            echo "Status: PROTECTED"
        else
            echo "Status: NOT PROTECTED -- run protect-sshd.sh"
        fi
    else
        echo "WARNING: sshd not running"
    fi

    # --- Network ---
    section "Network Interfaces"
    ip addr show 2>/dev/null | grep -E "^[0-9]+:|inet " || echo "(ip not available)"

    # --- Recent Reboots ---
    section "Recent Reboots"
    last reboot 2>/dev/null | head -10 || echo "(last not available)"

} | tee "$REPORT_FILE"

echo ""
echo "Report saved to: ${REPORT_FILE}"
