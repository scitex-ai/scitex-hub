<!-- ---
!-- Timestamp: 2025-10-18 14:15:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/POSTGRESQL_MIGRATION_GUIDE.md
!-- --- -->

# PostgreSQL Migration Guide for SciTeX Cloud

## Overview

This guide walks you through migrating SciTeX Cloud from SQLite to PostgreSQL for both development and production environments.

## Why PostgreSQL?

1. **Multi-user Support**: Better concurrency for multiple users
2. **Full-Text Search**: Advanced search capabilities for Scholar app
3. **JSON Fields**: Native support for complex data structures
4. **Production Parity**: Use same database in dev and prod
5. **Performance**: Better performance for complex queries
6. **Data Integrity**: Better transaction handling and constraints

## Prerequisites

### Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib libpq-dev

# Check PostgreSQL version
psql --version
```

### Start PostgreSQL Service

```bash
# Start service
sudo service postgresql start

# Enable auto-start on boot
sudo systemctl enable postgresql

# Check status
sudo service postgresql status
# or
pg_isready
```

## Step-by-Step Migration

### 1. Backup Current SQLite Database

```bash
# Navigate to project directory
cd /home/ywatanabe/proj/scitex-cloud

# Create backup
cp data/db/sqlite/scitex_cloud_dev.db data/db/backups/scitex_cloud_dev.db.backup_$(date +%Y%m%d_%H%M%S)

# Export data to JSON (for migration)
python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude contenttypes \
    --exclude auth.permission \
    --indent 2 \
    > data/db/backups/sqlite_data_export_$(date +%Y%m%d_%H%M%S).json
```

### 2. Create PostgreSQL Databases and Users

Run the setup script:

```bash
bash scripts/setup_postgres.sh
```

Or manually create databases:

```bash
# Switch to postgres user
sudo -u postgres psql

# Create development database and user
CREATE DATABASE scitex_cloud_dev;
CREATE USER scitex_dev WITH PASSWORD 'scitex_dev_2025';
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_dev TO scitex_dev;

# Create production database and user
CREATE DATABASE scitex_cloud_prod;
CREATE USER scitex_prod WITH PASSWORD 'CHANGE_THIS_IN_PRODUCTION';
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_prod TO scitex_prod;

# Enable extensions
\c scitex_cloud_dev
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

\c scitex_cloud_prod
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

# Grant schema permissions
\c scitex_cloud_dev
GRANT ALL ON SCHEMA public TO scitex_dev;
ALTER DATABASE scitex_cloud_dev OWNER TO scitex_dev;

\c scitex_cloud_prod
GRANT ALL ON SCHEMA public TO scitex_prod;
ALTER DATABASE scitex_cloud_prod OWNER TO scitex_prod;

# Exit psql
\q
```

### 3. Configure Environment Variables

Add to your shell environment (e.g., `~/.bashrc` or `~/.bash.d/secrets/001_ENV_SCITEX.src`):

```bash
# Development PostgreSQL
export SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev
export SCITEX_CLOUD_DB_USER_DEV=scitex_dev
export SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025
export SCITEX_CLOUD_DB_HOST_DEV=localhost
export SCITEX_CLOUD_DB_PORT_DEV=5432

# Production PostgreSQL
export SCITEX_CLOUD_DB_NAME_PROD=scitex_cloud_prod
export SCITEX_CLOUD_DB_USER_PROD=scitex_prod
export SCITEX_CLOUD_DB_PASSWORD_PROD=your_secure_password
export SCITEX_CLOUD_DB_HOST_PROD=localhost
export SCITEX_CLOUD_DB_PORT_PROD=5432

# Reload environment
source ~/.bashrc
# or
source ~/.bash.d/secrets/001_ENV_SCITEX.src
```

### 4. Verify Django Settings

The settings are already configured in `config/settings/settings_dev.py` and `config/settings/settings_prod.py`:

```python
# Development uses PostgreSQL by default
# Production uses PostgreSQL by default

# SQLite fallback available with:
# export SCITEX_CLOUD_USE_SQLITE_DEV=1
# export SCITEX_CLOUD_USE_SQLITE_PROD=1
```

### 5. Test PostgreSQL Connection

```bash
# Test connection
psql -U scitex_dev -h localhost -d scitex_cloud_dev -c "SELECT version();"

# Should prompt for password: scitex_dev_2025
```

### 6. Run Migrations

```bash
# Run Django migrations
python manage.py migrate

# Verify tables created
psql -U scitex_dev -d scitex_cloud_dev -c "\dt"
```

### 7. Load Data from SQLite Backup

```bash
# Load the JSON dump into PostgreSQL
python manage.py loaddata data/db/backups/sqlite_data_export_YYYYMMDD_HHMMSS.json

# If you get errors, you may need to load specific apps separately:
python manage.py loaddata data/db/backups/sqlite_data_export_YYYYMMDD_HHMMSS.json --exclude auth --exclude contenttypes
```

### 8. Create Superuser

```bash
# Create a new superuser
python manage.py createsuperuser

# Or change existing user password
python manage.py changepassword username
```

### 9. Verify Migration

```bash
# Start development server
python manage.py runserver

# Test in browser
# http://localhost:8000/admin

# Check database
python manage.py dbshell
# You should be in PostgreSQL, not SQLite

# Run this query to check
SELECT current_database(), version();
\dt
\q
```

### 10. Update Database Paths in Code (if needed)

The new data structure is:

```
data/
├── db/
│   ├── sqlite/          # SQLite databases (fallback only)
│   ├── backups/         # Database backups
│   └── migrations_archive/  # Old migrations
└── users/               # User-specific data
    ├── username1/
    ├── username2/
    └── .gitkeep
```

Settings already use:
- PostgreSQL: Connection via environment variables
- SQLite fallback: `data/db/sqlite/scitex_cloud_dev.db`

## Production Deployment

### For Production Server

1. **Secure Password**: Change default production password

```bash
sudo -u postgres psql
ALTER USER scitex_prod WITH PASSWORD 'your_very_secure_password';
\q
```

2. **Update Environment Variables**

```bash
export SCITEX_CLOUD_DB_PASSWORD_PROD='your_very_secure_password'
```

3. **Run Migrations**

```bash
python manage.py migrate --settings=config.settings.settings_prod
```

4. **Collect Static Files**

```bash
python manage.py collectstatic --noinput --settings=config.settings.settings_prod
```

5. **Start Production Server**

```bash
# Using systemd service
sudo systemctl start scitex_cloud
sudo systemctl status scitex_cloud
```

## Backup and Restore

### Automated Backups

Use the provided backup script:

```bash
# Run backup manually
bash scripts/backup_database.sh

# Or set up automated daily backups with cron
crontab -e

# Add this line for daily backup at 2 AM:
0 2 * * * cd /home/ywatanabe/proj/scitex-cloud && bash scripts/backup_database.sh >> logs/backup.log 2>&1
```

The script (`scripts/backup_database.sh`) automatically:
- Backs up both PostgreSQL databases (dev and prod)
- Backs up SQLite databases (if they exist)
- Compresses backups with gzip
- Removes backups older than 7 days
- Shows backup summary

### Manual Backup

```bash
# Backup development
pg_dump -U scitex_dev scitex_cloud_dev > \
    data/db/backups/scitex_cloud_dev_$(date +%Y%m%d_%H%M%S).sql

# Backup production
pg_dump -U scitex_prod scitex_cloud_prod > \
    data/db/backups/scitex_cloud_prod_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

```bash
# Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS scitex_cloud_dev;
CREATE DATABASE scitex_cloud_dev OWNER scitex_dev;
EOF

# Restore from backup
psql -U scitex_dev scitex_cloud_dev < \
    data/db/backups/scitex_cloud_dev_YYYYMMDD_HHMMSS.sql
```

## Rollback to SQLite (if needed)

If you need to rollback to SQLite:

```bash
# Set environment variable
export SCITEX_CLOUD_USE_SQLITE_DEV=1

# Restore SQLite backup
cp data/db/backups/scitex_cloud_dev.db.backup_YYYYMMDD_HHMMSS \
   data/db/sqlite/scitex_cloud_dev.db

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

## Troubleshooting

### Permission Denied

```bash
# Grant all privileges
sudo -u postgres psql << EOF
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_dev TO scitex_dev;
\c scitex_cloud_dev
GRANT ALL ON SCHEMA public TO scitex_dev;
GRANT ALL ON ALL TABLES IN SCHEMA public TO scitex_dev;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO scitex_dev;
EOF
```

### Connection Refused

```bash
# Check PostgreSQL is running
pg_isready
sudo service postgresql status

# Check PostgreSQL is listening
sudo netstat -plnt | grep 5432

# Check pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add this line if not present:
# local   all             all                                     md5
```

### Migration Errors

```bash
# Reset migrations (CAREFUL - this deletes data!)
python manage.py migrate --fake app_name zero
python manage.py migrate app_name

# Or recreate database
sudo -u postgres psql << EOF
DROP DATABASE scitex_cloud_dev;
CREATE DATABASE scitex_cloud_dev OWNER scitex_dev;
EOF

python manage.py migrate
```

### Data Import Errors

```bash
# Try loading specific apps
python manage.py loaddata backup.json --app scholar_app
python manage.py loaddata backup.json --app code_app

# Skip problematic apps
python manage.py loaddata backup.json --exclude auth --exclude contenttypes
```

## Performance Tuning

### PostgreSQL Configuration

Edit `/etc/postgresql/*/main/postgresql.conf`:

```conf
# Connection settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# Performance
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging (for debugging)
log_statement = 'all'
log_duration = on
```

Restart PostgreSQL:

```bash
sudo service postgresql restart
```

### Django Settings

Already configured in `settings_shared.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pooling
        'ATOMIC_REQUESTS': True,  # Transaction management
    }
}
```

## Monitoring

### Check Database Size

```bash
psql -U scitex_dev -d scitex_cloud_dev -c "
SELECT
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'scitex_cloud_dev';
"
```

### Check Active Connections

```bash
psql -U scitex_dev -d scitex_cloud_dev -c "
SELECT count(*) FROM pg_stat_activity WHERE datname = 'scitex_cloud_dev';
"
```

### View Table Sizes

```bash
psql -U scitex_dev -d scitex_cloud_dev -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

## Summary Checklist

- [ ] PostgreSQL installed and running
- [ ] SQLite database backed up
- [ ] PostgreSQL databases created (dev & prod)
- [ ] Environment variables configured
- [ ] Django migrations run successfully
- [ ] Data loaded from SQLite backup
- [ ] Superuser created
- [ ] Application tested and working
- [ ] Backup script created and scheduled
- [ ] Documentation updated

## See Also

- `config/deployment/02_POSTGRESQL_SETUP.md` - PostgreSQL setup
- `config/deployment/nginx/README.md` - Nginx configuration
- `config/deployment/03_UWSGI_SETUP.md` - uWSGI setup
- `docs/ENVIRONMENT_VARIABLES.md` - Environment variables

## Questions?

If you encounter issues not covered here, check:
1. PostgreSQL logs: `/var/log/postgresql/`
2. Django logs: `logs/django.log`
3. uWSGI logs: `/var/log/uwsgi/scitex_cloud.log`

<!-- EOF -->
