# SciTeX Dev - Windows Port Forwarding Setup
# Run as Administrator (right-click → Run as Administrator)
# Auto-detects WSL IP and sets up port forwarding for iPhone dev testing.

$ErrorActionPreference = "Continue"

# Ports to forward
$ports = @(8000, 5173)

# Get WSL IP
$wslIp = (wsl hostname -I).Trim().Split(" ")[0]
if (-not $wslIp) {
    Write-Host "ERROR: Could not detect WSL IP" -ForegroundColor Red
    exit 1
}
Write-Host "WSL IP: $wslIp" -ForegroundColor Cyan

# Get Windows LAN IP
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -match 'Wi-Fi|Ethernet' -and $_.PrefixOrigin -eq 'Dhcp' }
).IPAddress | Select-Object -First 1

if ($lanIp) {
    Write-Host "Windows LAN IP: $lanIp" -ForegroundColor Cyan
    Write-Host "iPhone access: http://${lanIp}:8000" -ForegroundColor Green
}

# Setup port forwarding
foreach ($port in $ports) {
    Write-Host "  Port $port → ${wslIp}:$port" -ForegroundColor Yellow

    # Remove existing
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null

    # Add new
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIp

    # Firewall rule
    $ruleName = "SciTeX Dev $port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
        Write-Host "  Firewall rule added: $ruleName" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Port forwarding setup complete!" -ForegroundColor Green
Write-Host ""
netsh interface portproxy show all
Write-Host ""
Write-Host "Press Enter to close..." -ForegroundColor Gray
Read-Host
