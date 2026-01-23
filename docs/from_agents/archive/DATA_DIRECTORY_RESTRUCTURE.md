<!-- ---
!-- Timestamp: 2025-10-18 14:20:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/DATA_DIRECTORY_RESTRUCTURE.md
!-- --- -->

# Data Directory Restructure

## Overview

The `./data/` directory has been reorganized to provide better separation between database files and user-specific data, improving maintainability and backup strategies.

## New Directory Structure

```
data/
├── db/                         # All database-related files
│   ├── sqlite/                 # SQLite database files (fallback only)
│   │   ├── .gitkeep
│   │   ├── scitex_cloud_dev.db
│   │   └── scitex_cloud_prod.db
│   ├── backups/                # Database backups (SQLite & PostgreSQL dumps)
│   │   ├── .gitkeep
│   │   └── *.sql / *.db
│   └── migrations_archive/     # Archived Django migrations
│       ├── .gitkeep
│       └── old_migrations/
└── users/                      # User-specific workspace data
    ├── .gitkeep
    ├── {username1}/            # Per-user directory
    │   ├── proj/
    │   ├── projects/
    │   ├── shared/
    │   ├── temp/
    │   └── workspace_info.json
    └── {username2}/
        └── ...
```

## Migration from Old Structure

### Old Structure (Before)

```
data/
├── scitex_cloud_dev.db         # Development SQLite DB
├── scitex_cloud_prod.db        # Production SQLite DB
├── backups/                    # Database backups
├── migrations_backup/          # Migration archives
├── ywatanabe1989/             # User data
├── ywatanabe/                 # User data
└── wyusuuke/                  # User data
```

### New Structure (After)

```
data/
├── db/
│   ├── sqlite/
│   │   ├── scitex_cloud_dev.db
│   │   └── scitex_cloud_prod.db
│   ├── backups/
│   └── migrations_archive/
└── users/
    ├── ywatanabe1989/
    ├── ywatanabe/
    └── wyusuuke/
```

## Changes Made

### 1. Directory Organization

Created new subdirectory structure:
```bash
data/
├── db/sqlite/
├── db/backups/
├── db/migrations_archive/
└── users/
```

### 2. File Moves

- **Database files**: Moved to `data/db/sqlite/`
- **Backups**: Moved to `data/db/backups/`
- **Migrations**: Moved to `data/db/migrations_archive/`
- **User data**: Moved to `data/users/{username}/`

### 3. Settings Updates

Updated Django settings to reference new paths:

#### `config/settings/settings_dev.py`
```python
# SQLite fallback path
"NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_cloud_dev.db"
```

#### `config/settings/settings_prod.py`
```python
# SQLite fallback path
"NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_cloud_prod.db"
```

#### `config/settings/settings_shared.py`
```python
# Base fallback path
"NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_cloud.db"
```

### 4. .gitignore Updates

Updated to track directory structure while ignoring contents:

```gitignore
# Data directories - specific patterns to ignore
data/db/sqlite/*.db*
data/db/backups/*
data/db/migrations_archive/*
data/users/*/

# Keep directory structure with .gitkeep files
!data/db/sqlite/.gitkeep
!data/db/backups/.gitkeep
!data/db/migrations_archive/.gitkeep
!data/users/.gitkeep
```

### 5. .gitkeep Files

Added `.gitkeep` files to maintain directory structure in git:
- `data/db/sqlite/.gitkeep`
- `data/db/backups/.gitkeep`
- `data/db/migrations_archive/.gitkeep`
- `data/users/.gitkeep`

## Benefits

### 1. Better Organization
- Clear separation between database and user data
- Easier to understand directory structure
- Consistent with Django best practices

### 2. Improved Backup Strategy
- Can backup `data/db/` and `data/users/` separately
- Database backups isolated in `data/db/backups/`
- User data isolated in `data/users/`

### 3. Better .gitignore Management
- More granular control over what's tracked
- Directory structure tracked, contents ignored
- Clearer intent for each subdirectory

### 4. PostgreSQL Migration Ready
- SQLite files clearly marked as fallback
- PostgreSQL backups go to `data/db/backups/`
- Migration archives in dedicated directory

### 5. Production Deployment
- Easy to mount different volumes for db vs users
- Better security (different permissions for db and users)
- Easier to scale (users can be on separate storage)

## Database Configuration

### Primary: PostgreSQL (Default)

Both development and production use PostgreSQL by default:

```bash
# Development
SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev
SCITEX_CLOUD_DB_USER_DEV=scitex_dev
SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025

# Production
SCITEX_CLOUD_DB_NAME_PROD=scitex_cloud_prod
SCITEX_CLOUD_DB_USER_PROD=scitex_prod
SCITEX_CLOUD_DB_PASSWORD_PROD=your_secure_password
```

### Fallback: SQLite

SQLite is available as a fallback:

```bash
# Development
export SCITEX_CLOUD_USE_SQLITE_DEV=1

# Production
export SCITEX_CLOUD_USE_SQLITE_PROD=1
```

SQLite files are stored in `data/db/sqlite/`:
- `scitex_cloud_dev.db` - Development database
- `scitex_cloud_prod.db` - Production database
- `scitex_cloud.db` - Base fallback database

## User Data Management

User-specific data is stored in `data/users/{username}/`:

```
data/users/{username}/
├── proj/                    # User's research projects
├── projects/                # Legacy projects
├── shared/                  # Shared workspace files
├── temp/                    # Temporary files
└── workspace_info.json      # Workspace metadata
```

### Example Access in Code

```python
from pathlib import Path
from django.conf import settings

def get_user_data_dir(username):
    """Get user-specific data directory."""
    return settings.BASE_DIR / "data" / "users" / username

def get_user_project_dir(username, project_name):
    """Get user's specific project directory."""
    return get_user_data_dir(username) / "proj" / project_name
```

## Backup Procedures

### Database Backups

#### PostgreSQL
```bash
# Backup development database
pg_dump -U scitex_dev scitex_cloud_dev > \
    data/db/backups/scitex_cloud_dev_$(date +%Y%m%d_%H%M%S).sql

# Backup production database
pg_dump -U scitex_prod scitex_cloud_prod > \
    data/db/backups/scitex_cloud_prod_$(date +%Y%m%d_%H%M%S).sql
```

#### SQLite
```bash
# Backup development database
cp data/db/sqlite/scitex_cloud_dev.db \
   data/db/backups/scitex_cloud_dev_$(date +%Y%m%d_%H%M%S).db
```

### User Data Backups

```bash
# Backup all user data
tar -czf data_users_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/users/

# Backup specific user
tar -czf user_backup_${username}_$(date +%Y%m%d_%H%M%S).tar.gz \
    data/users/${username}/
```

### Automated Backup Script

See `tmp/backup_postgres.sh` for automated PostgreSQL backups.

## Restore Procedures

### From PostgreSQL Backup

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

### From SQLite Backup

```bash
# Restore database
cp data/db/backups/scitex_cloud_dev_YYYYMMDD_HHMMSS.db \
   data/db/sqlite/scitex_cloud_dev.db
```

### From User Data Backup

```bash
# Restore all users
tar -xzf data_users_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore specific user
tar -xzf user_backup_${username}_YYYYMMDD_HHMMSS.tar.gz
```

## Migration Checklist

If you're working on this project, verify:

- [ ] Database files are in `data/db/sqlite/`
- [ ] Backups are in `data/db/backups/`
- [ ] User data is in `data/users/{username}/`
- [ ] Settings files reference correct paths
- [ ] .gitkeep files exist in all subdirectories
- [ ] .gitignore properly configured
- [ ] PostgreSQL is primary database
- [ ] SQLite fallback works

## Testing the New Structure

### Test Database Paths

```bash
# Development with PostgreSQL (default)
python manage.py check --settings=config.settings.settings_dev

# Development with SQLite fallback
export SCITEX_CLOUD_USE_SQLITE_DEV=1
python manage.py check --settings=config.settings.settings_dev

# Production with PostgreSQL (default)
python manage.py check --settings=config.settings.settings_prod

# Production with SQLite fallback
export SCITEX_CLOUD_USE_SQLITE_PROD=1
python manage.py check --settings=config.settings.settings_prod
```

### Test User Data Access

```python
from pathlib import Path
from django.conf import settings

# Check user directory exists
user_dir = settings.BASE_DIR / "data" / "users" / "test_user"
assert user_dir.parent.exists(), "users/ directory should exist"

# Check .gitkeep files
assert (settings.BASE_DIR / "data" / "db" / "sqlite" / ".gitkeep").exists()
assert (settings.BASE_DIR / "data" / "db" / "backups" / ".gitkeep").exists()
assert (settings.BASE_DIR / "data" / "users" / ".gitkeep").exists()
```

## Troubleshooting

### Database Not Found

If you get "database not found" errors:

```bash
# Check database location
ls -la data/db/sqlite/

# Verify settings
python manage.py diffsettings | grep DATABASE
```

### User Data Not Found

If user workspace data is missing:

```bash
# Check user directory
ls -la data/users/{username}/

# Verify path in code
grep -r "data/users" apps/
```

### Permission Issues

```bash
# Fix permissions for database directory
chmod 755 data/db/sqlite/
chmod 644 data/db/sqlite/*.db

# Fix permissions for user directories
chmod 755 data/users/
chmod 755 data/users/*/
```

## See Also

- `docs/POSTGRESQL_MIGRATION_GUIDE.md` - PostgreSQL migration guide
- `config/deployment/02_POSTGRESQL_SETUP.md` - PostgreSQL setup
- `config/deployment/nginx/README.md` - Nginx configuration
- `docs/ENVIRONMENT_VARIABLES.md` - Environment variables

## Summary

The data directory restructure provides:
- ✅ Better organization with clear separation
- ✅ Improved backup and restore procedures
- ✅ PostgreSQL as primary database
- ✅ SQLite as fallback option
- ✅ User data isolation
- ✅ Production-ready structure
- ✅ Proper .gitignore configuration

<!-- EOF -->
