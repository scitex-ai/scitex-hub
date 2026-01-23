# PostgreSQL Setup

Database configuration for SciTeX Cloud

---

## Quick Start

```bash
# Setup PostgreSQL databases (dev + prod)
sudo ./setup_postgres.sh

# Or use SQL script directly
sudo -u postgres psql -f setup_postgres.sql
```

---

## Files

| File | Purpose |
|------|---------|
| `setup_postgres.sh` | Automated setup script |
| `setup_postgres.sql` | SQL setup script |

---

## Databases Created

| Database | User | Purpose |
|----------|------|---------|
| `scitex_cloud_dev` | `scitex_dev` | Development |
| `scitex_cloud_prod` | `scitex_prod` | Production |

**Passwords:** Auto-generated and stored in `~/.scitex_db_passwords`

---

## Common Operations

```bash
# Check PostgreSQL status
systemctl status postgresql

# Connect to database
psql -U scitex_dev -d scitex_cloud_dev

# Backup database
pg_dump scitex_cloud_prod > backup_$(date +%Y%m%d).sql

# Restore database
psql -U scitex_prod -d scitex_cloud_prod < backup.sql

# View databases
sudo -u postgres psql -c "\l"
```

---

## Troubleshooting

```bash
# Check if running
pg_isready

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check logs
sudo journalctl -u postgresql -f

# Check connection
python manage.py dbshell
```

---

**Status:** Production Ready

<!-- EOF -->
