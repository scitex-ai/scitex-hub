# uWSGI Configuration

Application server for SciTeX Cloud Django backend

---

## Quick Start

```bash
# Setup uWSGI service
sudo ./setup_uwsgi.sh

# Start service
sudo systemctl start uwsgi
```

---

## Files

| File | Purpose |
|------|---------|
| `setup_uwsgi.sh` | Automated setup script |
| `uwsgi.ini` | Production config (unified) |
| `uwsgi.service` | Systemd service file |
| `uwsgi_dev.ini` | Development config |
| `uwsgi_dev.service` | Dev systemd service |

---

## Architecture

```
Nginx → Unix Socket (/run/scitex_cloud.sock) → uWSGI → Django
```

---

## Service Management

```bash
# Start
sudo systemctl start uwsgi

# Stop
sudo systemctl stop uwsgi

# Restart
sudo systemctl restart uwsgi

# Status
sudo systemctl status uwsgi

# View logs
sudo journalctl -u uwsgi -f
```

---

## Configuration

**Production (`uwsgi.ini`):**
- Socket: `/run/scitex_cloud.sock`
- Workers: Auto (based on CPU cores)
- Chdir: `/home/ywatanabe/proj/scitex-cloud`
- Module: `config.wsgi:application`

**Development (`uwsgi_dev.ini`):**
- Similar to production but with debug settings
- Auto-reload on code changes

---

## Troubleshooting

```bash
# Check socket exists
ls -la /run/scitex_cloud.sock

# Check socket permissions
sudo -u www-data test -r /run/scitex_cloud.sock && echo "OK"

# View detailed logs
sudo journalctl -u uwsgi -n 100 --no-pager

# Test uWSGI directly
uwsgi --ini uwsgi.ini

# Check Django app
python manage.py check
```

---

**Status:** Production Ready  
**Socket:** `/run/scitex_cloud.sock`

<!-- EOF -->
