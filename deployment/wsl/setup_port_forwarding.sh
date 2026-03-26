#!/usr/bin/env bash
# Setup Windows port forwarding for iPhone dev testing.
# Run from WSL — executes PowerShell commands on Windows side.
#
# Forwards ports 8000 (Django) and 5173 (Vite HMR) from Windows LAN
# to WSL, so iPhones on the same WiFi can access local dev.
#
# Usage: ./scripts/setup/setup_port_forwarding.sh
# Called automatically by: make env=dev start (via Makefile)

set -euo pipefail

PORTS=(8000 5173)
WSL_IP=$(hostname -I | awk '{print $1}')

if [[ -z "$WSL_IP" ]]; then
    echo "ERROR: Could not detect WSL IP" >&2
    exit 1
fi

echo "WSL IP: $WSL_IP"
echo "Setting up port forwarding for ports: ${PORTS[*]}"

# Check if powershell.exe is available (WSL only)
if ! command -v powershell.exe &>/dev/null; then
    echo "SKIP: Not running in WSL (powershell.exe not found)"
    exit 0
fi

for port in "${PORTS[@]}"; do
    echo "  Port $port → $WSL_IP:$port"
    # Remove existing rule (ignore errors)
    powershell.exe -Command "
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>\$null
        netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$WSL_IP
    " 2>/dev/null || echo "  WARNING: Failed to set port $port (need admin PowerShell?)"
done

# Ensure firewall rules exist
for port in "${PORTS[@]}"; do
    powershell.exe -Command "
        if (-not (Get-NetFirewallRule -DisplayName 'SciTeX Dev $port' -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName 'SciTeX Dev $port' -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
            Write-Host '  Firewall rule added for port $port'
        }
    " 2>/dev/null || true
done

# Detect Windows LAN IP for VITE_HOST_IP
WIN_LAN_IP=$(powershell.exe -Command "
    (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.InterfaceAlias -match 'Wi-Fi|Ethernet' -and \$_.PrefixOrigin -eq 'Dhcp' }).IPAddress
" 2>/dev/null | tr -d '\r\n')

if [[ -n "$WIN_LAN_IP" ]]; then
    echo ""
    echo "Windows LAN IP: $WIN_LAN_IP"
    echo "iPhone access: http://$WIN_LAN_IP:8000"

    # Update VITE_HOST_IP in .env if it differs
    ENV_FILE="deployment/docker/docker_dev/.env"
    if [[ -f "$ENV_FILE" ]]; then
        CURRENT=$(grep -oP 'VITE_HOST_IP=\K.*' "$ENV_FILE" 2>/dev/null || echo "")
        if [[ "$CURRENT" != "$WIN_LAN_IP" ]]; then
            sed -i "s|VITE_HOST_IP=.*|VITE_HOST_IP=$WIN_LAN_IP|" "$ENV_FILE"
            echo "Updated VITE_HOST_IP=$WIN_LAN_IP in $ENV_FILE"
            echo "NOTE: Run 'make env=dev recreate' to apply"
        fi
    fi
else
    echo "WARNING: Could not detect Windows LAN IP"
fi

echo ""
echo "Port forwarding setup complete."
echo "Verify: powershell.exe -Command 'netsh interface portproxy show all'"
