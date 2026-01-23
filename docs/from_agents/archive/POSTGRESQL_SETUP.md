<!-- ---
!-- Timestamp: 2025-10-18 13:45:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/POSTGRESQL_SETUP.md
!-- --- -->

# PostgreSQL Setup for SciTeX Cloud

## Overview

SciTeX Cloud now uses PostgreSQL for both development and production environments. This provides:
- Better performance for multi-user scenarios
- Advanced full-text search for Scholar app
- JSON field support for complex data
- Production parity in development

## Quick Start

### 1. Run the Setup Script

```bash
bash scripts/setup_postgres.sh
```

This will:
- Create `scitex_cloud_dev` database with user `scitex_dev`
- Create `scitex_cloud_prod` database with user `scitex_prod`
- Enable PostgreSQL extensions (pg_trgm, unaccent)
- Set proper permissions

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
```

## Database Credentials

### Development
- **Database**: `scitex_cloud_dev`
- **User**: `scitex_dev`
- **Password**: `scitex_dev_2025`
- **Host**: `localhost`
- **Port**: `5432`

### Production (Local Testing)
- **Database**: `scitex_cloud_prod`
- **User**: `scitex_prod`
- **Password**: `CHANGE_THIS_IN_PRODUCTION`
- **Host**: `localhost`
- **Port**: `5432`

## PostgreSQL Management

### Start PostgreSQL Service

```bash
sudo service postgresql start
```

### Stop PostgreSQL Service

```bash
sudo service postgresql stop
```

### Check Status

```bash
sudo service postgresql status
# or
pg_isready
```

### Connect to Database

```bash
# Development
psql -U scitex_dev -d scitex_cloud_dev

# Production
psql -U scitex_prod -d scitex_cloud_prod

# As postgres superuser
sudo -u postgres psql
```

### Common PostgreSQL Commands

```sql
-- List databases
\l

-- Connect to database
\c scitex_cloud_dev

-- List tables
\dt

-- Describe table
\d table_name

-- List users
\du

-- Quit
\q
```

## Backup and Restore

### Backup Development Database

```bash
pg_dump -U scitex_dev scitex_cloud_dev > data/backups/scitex_cloud_dev_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Development Database

```bash
psql -U scitex_dev scitex_cloud_dev < data/backups/scitex_cloud_dev_YYYYMMDD_HHMMSS.sql
```

### Backup Production Database

```bash
pg_dump -U scitex_prod scitex_cloud_prod > data/backups/scitex_cloud_prod_$(date +%Y%m%d_%H%M%S).sql
```

## SQLite Fallback

Both development and production can fall back to SQLite if needed:

### Development SQLite

```bash
export SCITEX_CLOUD_USE_SQLITE_DEV=1
python manage.py runserver
```

### Production SQLite

```bash
export SCITEX_CLOUD_USE_SQLITE_PROD=1
python manage.py runserver --settings=config.settings.settings_prod
```

## Environment Variables

See `docs/ENVIRONMENT_VARIABLES.md` for complete documentation.

### Development Environment Variables

```bash
export SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev
export SCITEX_CLOUD_DB_USER_DEV=scitex_dev
export SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025
export SCITEX_CLOUD_DB_HOST_DEV=localhost
export SCITEX_CLOUD_DB_PORT_DEV=5432
```

### Production Environment Variables

```bash
export SCITEX_CLOUD_DB_NAME_PROD=scitex_cloud_prod
export SCITEX_CLOUD_DB_USER_PROD=scitex_prod
export SCITEX_CLOUD_DB_PASSWORD_PROD=your_secure_password
export SCITEX_CLOUD_DB_HOST_PROD=localhost
export SCITEX_CLOUD_DB_PORT_PROD=5432
```

## Troubleshooting

### PostgreSQL Service Won't Start

```bash
# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Restart service
sudo service postgresql restart
```

### Permission Denied Errors

```bash
# Grant all privileges (run as postgres user)
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_dev TO scitex_dev;"
```

### Connection Refused

```bash
# Check if PostgreSQL is running
pg_isready

# Check PostgreSQL configuration
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

### Reset Database

```bash
# Drop and recreate development database
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS scitex_cloud_dev;
CREATE DATABASE scitex_cloud_dev OWNER scitex_dev;
EOF

# Run migrations
python manage.py migrate
```

## Extensions Installed

- **pg_trgm**: Trigram matching for similarity searches
- **unaccent**: Accent-insensitive text search

To add more extensions:

```bash
sudo -u postgres psql -d scitex_cloud_dev -c "CREATE EXTENSION extension_name;"
```

## Performance Tuning

### Connection Pooling

Settings already configured in Django:
- `CONN_MAX_AGE = 600` (10 minutes)
- `ATOMIC_REQUESTS = True`

### Query Optimization

Enable SQL logging in development:

```bash
export SQL_DEBUG=1
python manage.py runserver
```

## Production Deployment

For remote PostgreSQL server:

1. Set environment variables:

```bash
export DB_PASSWORD="your_secure_password"
export DB_NAME="scitex_cloud_prod"
export DB_USER="scitex_prod"
export DB_HOST="your-db-host.com"
export DB_PORT="5432"
```

2. Update production password:

```sql
ALTER USER scitex_prod WITH PASSWORD 'your_new_secure_password';
```

## Security Recommendations

1. **Change default passwords** in production
2. **Use environment variables** for credentials
3. **Enable SSL** for remote connections
4. **Regular backups** (automated daily)
5. **Restrict network access** to database server

## Next Steps

1. ✅ PostgreSQL installed and configured
2. ✅ Databases created with proper users
3. ✅ Django settings updated
4. ⏳ Run migrations: `python manage.py migrate`
5. ⏳ Create superuser: `python manage.py createsuperuser`
6. ⏳ Test the application

<!-- EOF -->
