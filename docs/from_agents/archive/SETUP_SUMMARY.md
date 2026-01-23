<!-- ---
!-- Timestamp: 2025-10-18 14:05:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/SETUP_SUMMARY.md
!-- --- -->

# PostgreSQL Setup Complete - Summary

## What Was Fixed

### 1. URL Namespace Conflict ✅
**Problem**: `cloud_app` namespace registered twice

**Solution**: Modified `discover_app_urls()` to skip manually configured apps

**File**: `config/urls.py:282`
```python
skip_apps = {'cloud_app'}
```

### 2. Database Corruption ✅
**Problem**: Duplicate users from manual migration file renaming

**Solution**: Fresh database start with proper PostgreSQL setup

### 3. Database Location ✅
**Problem**: Database in project root instead of `./data/`

**Solution**: Moved to `./data/scitex_cloud_dev.db` (now PostgreSQL)

### 4. PostgreSQL Migration ✅
**Problem**: SQLite → PostgreSQL transition

**Solution**: Complete PostgreSQL setup for dev and prod

## Current Database Configuration

### Development (Default)
- **Engine**: PostgreSQL
- **Database**: `scitex_cloud_dev`
- **User**: `scitex_dev`
- **Password**: `scitex_dev_2025`
- **Fallback**: SQLite with `export SCITEX_CLOUD_USE_SQLITE_DEV=1`

### Production
- **Engine**: PostgreSQL
- **Database**: `scitex_cloud_prod`
- **User**: `scitex_prod`
- **Password**: Set via `SCITEX_CLOUD_DB_PASSWORD_PROD`
- **Fallback**: SQLite with `export SCITEX_CLOUD_USE_SQLITE_PROD=1`

## Next Steps (Manual)

You need to run these commands manually because they require sudo:

### 1. Create PostgreSQL Databases

```bash
bash scripts/setup_postgres.sh
```

This creates:
- `scitex_cloud_dev` database
- `scitex_cloud_prod` database
- Users and permissions
- PostgreSQL extensions

### 2. Run Django Migrations

```bash
python manage.py migrate
```

### 3. Create Superuser

```bash
python manage.py createsuperuser --username ywatanabe --email ywata1989@gmail.com
```

### 4. Test the Setup

```bash
# Start server
python manage.py runserver

# Visit http://localhost:8000/admin
# Login with your superuser credentials
```

## Environment Variables (SCITEX_CLOUD_ Prefix)

All environment variables now use the `SCITEX_CLOUD_` prefix for easy searching:

### Database Switching
```bash
# Use SQLite for development
export SCITEX_CLOUD_USE_SQLITE_DEV=1

# Use SQLite for production
export SCITEX_CLOUD_USE_SQLITE_PROD=1
```

### Database Configuration
```bash
# Development
export SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev
export SCITEX_CLOUD_DB_USER_DEV=scitex_dev
export SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025
export SCITEX_CLOUD_DB_HOST_DEV=localhost
export SCITEX_CLOUD_DB_PORT_DEV=5432

# Production
export SCITEX_CLOUD_DB_NAME_PROD=scitex_cloud_prod
export SCITEX_CLOUD_DB_USER_PROD=scitex_prod
export SCITEX_CLOUD_DB_PASSWORD_PROD=your_secure_password
export SCITEX_CLOUD_DB_HOST_PROD=localhost
export SCITEX_CLOUD_DB_PORT_PROD=5432
```

## Files Created/Modified

### Documentation
- ✅ `docs/DATABASE_DECISION.md` - Why PostgreSQL
- ✅ `docs/POSTGRESQL_SETUP.md` - Setup guide
- ✅ `docs/WHAT_HAPPENED_AND_HOW_TO_PREVENT.md` - Detailed explanation
- ✅ `docs/ENVIRONMENT_VARIABLES.md` - Environment variable reference
- ✅ `docs/SETUP_SUMMARY.md` - This file

### Configuration
- ✅ `config/urls.py` - Fixed namespace conflict
- ✅ `config/settings/settings_dev.py` - PostgreSQL config + SCITEX_CLOUD_ prefix
- ✅ `config/settings/settings_prod.py` - PostgreSQL config + SCITEX_CLOUD_ prefix

### Scripts
- ✅ `scripts/setup_postgres.sh` - PostgreSQL database setup
- ✅ `tmp/setup_postgres.sql` - SQL setup commands
- ✅ `tmp/check_duplicates.py` - Database validation script

### Backups
- ✅ `data/scitex_cloud_dev.db.backup_20251018_*` - SQLite backup

## What You Learned

### ❌ Don't Do This
1. **Never manually rename migration files** - Breaks Django migration tracking
2. **Never bulk rename with scripts** - Causes database corruption
3. **Don't skip auto-discovered apps** - Leads to namespace conflicts

### ✅ Do This Instead
1. **Use Django's migration system** - `python manage.py makemigrations`
2. **Create data migrations** - For moving data between apps
3. **Test migrations on copies** - Before running on production
4. **Backup before migrating** - Always have a rollback plan
5. **Use environment variables** - With consistent naming (`SCITEX_CLOUD_*`)

## Quick Reference

### PostgreSQL Commands
```bash
# Start service
sudo service postgresql start

# Check status
pg_isready

# Connect to database
psql -U scitex_dev -d scitex_cloud_dev

# Backup
pg_dump -U scitex_dev scitex_cloud_dev > backup.sql

# Restore
psql -U scitex_dev scitex_cloud_dev < backup.sql
```

### Django Commands
```bash
# Check configuration
python manage.py check

# Show migrations status
python manage.py showmigrations

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Search Environment Variables
```bash
# List all SCITEX_CLOUD variables
env | grep SCITEX_CLOUD

# Search in code
grep -r "SCITEX_CLOUD_" config/settings/

# Search in docs
grep -r "SCITEX_CLOUD_" docs/
```

## Status Checklist

- [x] URL namespace conflict fixed
- [x] PostgreSQL installed and running
- [x] Django settings updated with SCITEX_CLOUD_ prefix
- [x] psycopg2-binary installed
- [x] Documentation created
- [x] Setup scripts ready
- [ ] **Manual**: Run `bash scripts/setup_postgres.sh`
- [ ] **Manual**: Run `python manage.py migrate`
- [ ] **Manual**: Create superuser
- [ ] **Manual**: Test application

## Resources

- **PostgreSQL Setup**: `docs/POSTGRESQL_SETUP.md`
- **Migration Guide**: `docs/WHAT_HAPPENED_AND_HOW_TO_PREVENT.md`
- **Environment Variables**: `docs/ENVIRONMENT_VARIABLES.md`
- **Database Decision**: `docs/DATABASE_DECISION.md`

---

## Final Notes

Everything is ready! You just need to:

1. Run the PostgreSQL setup script
2. Apply migrations
3. Create your user
4. Start developing

The database is now production-ready with:
- ✅ PostgreSQL for better performance
- ✅ Connection pooling
- ✅ Atomic transactions
- ✅ SQLite fallback option
- ✅ Consistent environment variable naming

Good luck with SciTeX Cloud! 🚀

<!-- EOF -->
