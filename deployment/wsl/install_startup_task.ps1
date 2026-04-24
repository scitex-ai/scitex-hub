# Install Windows Scheduled Task for SciTeX port forwarding
# Run as Administrator ONCE — after this, ports auto-forward on every login.

$ErrorActionPreference = "Stop"

$taskName = "SciTeX-PortForward"
$scriptPath = "$PSScriptRoot\setup_port_forwarding.ps1"

# Remove existing task
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create task that runs on user logon
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Auto-forward WSL ports for SciTeX iPhone dev testing"

Write-Host ""
Write-Host "Scheduled task '$taskName' installed!" -ForegroundColor Green
Write-Host "Ports will auto-forward on every Windows login." -ForegroundColor Cyan
Write-Host ""
Write-Host "To run now:  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
Write-Host "To remove:   Unregister-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
Write-Host ""

# Run it now
Start-ScheduledTask -TaskName $taskName
Write-Host "Running now..." -ForegroundColor Green

Write-Host "Press Enter to close..." -ForegroundColor Gray
Read-Host
