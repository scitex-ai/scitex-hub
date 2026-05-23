# Mobile Device Testing (LAN Access)

Access the local dev server from iPhone/iPad on the same WiFi network.

## Architecture

```
iPhone (192.168.0.x)
  → Windows LAN IP (192.168.0.67:8000, :5173)
    → WSL port proxy (172.19.33.56:8000, :5173)
      → Docker dev containers (0.0.0.0:8000, :5173)
```

## Setup Steps

### 1. Find IPs

```bash
# WSL IP (inside WSL terminal)
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
# Example: 172.19.33.56

# Windows LAN IP (PowerShell)
# ipconfig | findstr "IPv4"
# Example: 192.168.0.67
```

### 2. Windows Port Proxy (PowerShell as Admin)

Forward ports 8000 (Django) and 5173 (Vite HMR) from Windows to WSL:

```powershell
# Replace 172.19.33.56 with your WSL IP
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=172.19.33.56
netsh interface portproxy add v4tov4 listenport=5173 listenaddress=0.0.0.0 connectport=5173 connectaddress=172.19.33.56
```

### 3. Windows Firewall (PowerShell as Admin)

```powershell
New-NetFirewallRule -DisplayName "SciTeX Dev" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "SciTeX Vite" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
```

### 4. Django Settings

Set `VITE_HOST_IP` in `deployment/docker/docker_dev/.env`:

```
VITE_HOST_IP=192.168.0.67
```

This makes Django templates reference Vite assets at `http://192.168.0.67:5173/` instead of `http://127.0.0.1:5173/`, allowing the iPhone browser to load them.

### 5. Restart Dev Server

```bash
cd /path/to/scitex-hub
make ENV=dev restart
```

### 6. Access from iPhone

Open Safari: `http://192.168.0.67:8000`

## Cleanup

Remove port proxy rules when done:

```powershell
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=5173 listenaddress=0.0.0.0
```

Remove firewall rules:

```powershell
Remove-NetFirewallRule -DisplayName "SciTeX Dev"
Remove-NetFirewallRule -DisplayName "SciTeX Vite"
```

Reset `VITE_HOST_IP` in `.env`:

```
# VITE_HOST_IP=192.168.0.67
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Blank page | Port proxy not set | Run netsh commands |
| "Loading..." spinner | Vite assets at 127.0.0.1 | Set VITE_HOST_IP |
| Connection refused | Firewall blocking | Add firewall rules |
| WSL IP changed | DHCP reassigned WSL IP | Update netsh connectaddress |

## Notes

- WSL IP changes on reboot. Re-run netsh commands with new IP.
- `ALLOWED_HOSTS = '*'` is already set in dev settings.
- Vite HMR websocket auto-detects host from page URL (no extra config needed).
