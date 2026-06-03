# WSL Port Forwarding for iPhone Dev Testing

Forward ports from Windows LAN to WSL so iPhones on the same WiFi can access the local dev server.

## Quick Start

1. Open **PowerShell as Administrator** (right-click → Run as Administrator)
2. Run:

```powershell
cd \\wsl$\Ubuntu\home\ywatanabe\proj\scitex-hub\deployment\wsl
.\install_startup_task.ps1
```

Done. Ports auto-forward on every Windows login from now on.

## What It Does

| Port | Service | Purpose |
|------|---------|---------|
| 8000 | Django  | Main app |
| 5173 | Vite    | JS/CSS hot-reload |

- Detects WSL IP automatically (changes on every WSL restart)
- Detects Windows LAN IP for iPhone access URL
- Creates Windows Firewall rules
- Registers a Scheduled Task for auto-setup on login

## Files

| File | Purpose | When to Run |
|------|---------|-------------|
| `install_startup_task.ps1` | Register auto-start task | Once (as Admin) |
| `setup_port_forwarding.ps1` | Set up port forwarding | Auto (via task) or manual |
| `setup_port_forwarding.sh` | WSL-side wrapper | Optional (needs Admin) |

## Manual Run

If ports stop working (e.g., after WSL restart):

```powershell
# PowerShell (Admin)
cd \\wsl$\Ubuntu\home\ywatanabe\proj\scitex-hub\deployment\wsl
.\setup_port_forwarding.ps1
```

Or from WSL:

```bash
# Needs Admin PowerShell — will show UAC dialog
bash deployment/wsl/setup_port_forwarding.sh
```

## Verify

```powershell
netsh interface portproxy show all
```

Should show:

```
Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
0.0.0.0         8000        172.x.x.x       8000
0.0.0.0         5173        172.x.x.x       5173
```

## iPhone Access

After setup, access local dev from iPhone:

```
http://<Windows-LAN-IP>:8000
```

The script prints the correct URL. Typically `http://192.168.0.67:8000`.

## Troubleshooting

- **"Requires elevation"**: Run PowerShell as Administrator
- **iPhone still loading**: Check `VITE_HOST_IP` in `deployment/docker/docker_dev/.env` matches Windows LAN IP
- **WSL IP changed**: Run `setup_port_forwarding.ps1` again (or restart Windows to trigger scheduled task)
- **Remove auto-start**: `Unregister-ScheduledTask -TaskName "SciTeX-PortForward"`
