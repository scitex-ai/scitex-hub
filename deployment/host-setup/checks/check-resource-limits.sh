#!/bin/bash
# Check systemd resource limits that protect NAS from Docker build crashes.
# These limits prevent builds from starving sshd (2026-03-23 incident).
#
# Expected config:
#   /etc/systemd/system/containerd.service.d/resource-limit.conf  (CPUQuota=80%)
#   /etc/systemd/system/docker.service.d/resource-limit.conf      (CPUQuota=90%)
#   /etc/systemd/system/ssh.service.d/protect.conf                (OOMScoreAdjust=-900)

# shellcheck disable=SC1091
source "$(dirname "$0")/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
}

echo "🛡️  Resource Limits:"

errors=0

# 1. containerd CPU limit (protects against raw docker build)
containerd_cpu=$(cat /sys/fs/cgroup/system.slice/containerd.service/cpu.max 2>/dev/null || echo "missing")
if echo "$containerd_cpu" | grep -qE '^[0-9]+ [0-9]+$'; then
    echo -e "  ${GREEN}[OK]${NC} containerd CPU: ${containerd_cpu} ($(awk '{printf "%.0f%%", $1/$2*100}' <<<"$containerd_cpu"))"
else
    echo -e "  ${RED}[FAIL] containerd CPU limit NOT set${NC}"
    echo -e "  ${YELLOW}  Fix: create /etc/systemd/system/containerd.service.d/resource-limit.conf${NC}"
    echo -e "  ${YELLOW}  See: skill:scitex-hub → production-deployment.md → NAS Resource Protection${NC}"
    errors=$((errors + 1))
fi

# 2. docker CPU limit
docker_cpu=$(cat /sys/fs/cgroup/system.slice/docker.service/cpu.max 2>/dev/null || echo "missing")
if echo "$docker_cpu" | grep -qE '^[0-9]+ [0-9]+$'; then
    echo -e "  ${GREEN}[OK]${NC} docker CPU: ${docker_cpu} ($(awk '{printf "%.0f%%", $1/$2*100}' <<<"$docker_cpu"))"
else
    echo -e "  ${RED}[FAIL] docker CPU limit NOT set${NC}"
    errors=$((errors + 1))
fi

# 3. sshd OOM protection
sshd_oom=$(systemctl show ssh 2>/dev/null | grep -oP 'OOMScoreAdjust=\K-?[0-9]+' || echo "0")
if [ "$sshd_oom" -le -500 ] 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC} sshd OOMScoreAdjust: ${sshd_oom}"
else
    echo -e "  ${RED}[FAIL] sshd OOMScoreAdjust=${sshd_oom} (should be <= -500)${NC}"
    echo -e "  ${YELLOW}  Fix: create /etc/systemd/system/ssh.service.d/protect.conf${NC}"
    errors=$((errors + 1))
fi

# 4. sshd CPU weight
sshd_weight=$(systemctl show ssh 2>/dev/null | grep -oP 'CPUWeight=\K[0-9]+' || echo "100")
if [ "$sshd_weight" -ge 500 ] 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC} sshd CPUWeight: ${sshd_weight}"
else
    echo -e "  ${YELLOW}[WARN] sshd CPUWeight=${sshd_weight} (recommend >= 500)${NC}"
fi

if [ "$errors" -gt 0 ]; then
    echo ""
    echo -e "  ${RED}⚠️  $errors protection(s) missing — Docker builds may crash NAS${NC}"
fi
