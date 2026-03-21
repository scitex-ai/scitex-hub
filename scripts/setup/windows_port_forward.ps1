# Windows Port Forwarding for WSL2 - Local Network Access
# Run as Administrator in PowerShell
#
# This allows iPhone/other devices on the same network to access
# the dev server running in WSL2/Docker.
#
# Usage: Right-click PowerShell - Run as Administrator - paste this script

$WSL_IP = (wsl hostname -I).Trim().Split(" ")[0]
$PORTS = @(8000, 5173)

Write-Host "WSL2 IP: $WSL_IP" -ForegroundColor Cyan

foreach ($port in $PORTS) {
    # Remove existing rule if any
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null

    # Add port forward
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$WSL_IP

    # Add firewall rule (idempotent)
    $ruleName = "SciTeX Dev Port $port"
    $existing = netsh advfirewall firewall show rule name=$ruleName 2>$null
    if ($LASTEXITCODE -ne 0) {
        netsh advfirewall firewall add rule name=$ruleName dir=in action=allow protocol=tcp localport=$port
    }

    Write-Host "  Port $port forwarded to ${WSL_IP} port $port" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Access from iPhone:" -ForegroundColor Cyan
$WIN_IP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "172.*" } | Select-Object -First 1).IPAddress
Write-Host "  http://${WIN_IP}:8000/" -ForegroundColor Yellow
Write-Host "  http://${WIN_IP}:8000/status/" -ForegroundColor Yellow
