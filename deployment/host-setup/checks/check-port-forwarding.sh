#!/bin/bash
# Check WSL port forwarding status for iPhone dev testing

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
}

echo "📱 Port Forwarding (iPhone Dev):"

if ! command -v powershell.exe &>/dev/null; then
    echo "  [SKIP] Not WSL"
    exit 0
fi

# Check port proxy rules
proxy_output=$(powershell.exe -Command "netsh interface portproxy show all" 2>/dev/null | tr -d '\r')

port_8000=$(echo "$proxy_output" | grep -c "8000" || true)
port_5173=$(echo "$proxy_output" | grep -c "5173" || true)

if [ "$port_8000" -gt 0 ] && [ "$port_5173" -gt 0 ]; then
    echo -e "  ${GREEN}[OK] Port 8000 (Django) forwarded${NC}"
    echo -e "  ${GREEN}[OK] Port 5173 (Vite)   forwarded${NC}"
else
    [ "$port_8000" -eq 0 ] && echo -e "  ${RED}[ERR] Port 8000 (Django) NOT forwarded${NC}"
    [ "$port_5173" -eq 0 ] && echo -e "  ${RED}[ERR] Port 5173 (Vite)   NOT forwarded${NC}"
    echo -e "  ${YELLOW}Fix: bash deployment/wsl/setup_port_forwarding.sh${NC}"
fi

# Show iPhone access URL
win_ip=$(powershell.exe -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.InterfaceAlias -match 'Wi-Fi|Ethernet' -and \$_.PrefixOrigin -eq 'Dhcp' }).IPAddress | Select-Object -First 1" 2>/dev/null | tr -d '\r\n')
if [ -n "$win_ip" ]; then
    echo -e "  iPhone: http://${win_ip}:8000"
fi

# Check VITE_HOST_IP matches
env_file="$(dirname "${BASH_SOURCE[0]}")/../../../deployment/docker/docker_dev/.env"
if [ -f "$env_file" ]; then
    vite_ip=$(grep -oP 'VITE_HOST_IP=\K.*' "$env_file" 2>/dev/null || echo "")
    if [ -n "$win_ip" ] && [ "$vite_ip" != "$win_ip" ]; then
        echo -e "  ${YELLOW}[WARN] VITE_HOST_IP=$vite_ip but LAN IP=$win_ip${NC}"
        echo -e "  ${YELLOW}  Update .env and recreate: make env=dev recreate${NC}"
    fi
fi
