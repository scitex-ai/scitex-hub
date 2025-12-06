<!-- ---
!-- Timestamp: 2025-10-18 13:35:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/DATABASE_DECISION.md
!-- --- -->

# Database Decision: SQLite vs PostgreSQL for SciTeX Cloud

## Current Status
- Django 5.2.7
- Currently using SQLite (development)
- Single user environment (development phase)

## Analysis

### SQLite Advantages
✅ **Simple Setup**: Zero configuration, single file
✅ **Development Speed**: Perfect for rapid prototyping
✅ **Backup/Restore**: Simple file copy
✅ **Django 5.2 Support**: Full support with improved performance
✅ **Current Phase**: Ideal for solo development
✅ **WSL Compatible**: Works well in WSL environment

### SQLite Limitations
❌ **Concurrency**: Poor performance with multiple simultaneous writes
❌ **Production Scaling**: Not recommended for production with multiple users
❌ **Advanced Features**: Missing some PostgreSQL-specific features:
  - Full-text search (PostgreSQL has superior FTS)
  - JSON operations (limited compared to PostgreSQL)
  - Array fields, custom types
  - Advanced indexing (GiST, GIN, etc.)
❌ **No Network Access**: Can't connect remotely

### PostgreSQL Advantages
✅ **Production Ready**: Industry standard for Django applications
✅ **Concurrency**: Excellent multi-user support
✅ **Advanced Features**:
  - Full-text search with ranking
  - JSONField with advanced querying
  - ArrayField, HStoreField
  - Custom types and extensions
✅ **Data Integrity**: Better constraint enforcement
✅ **Scholar Features**: Perfect for academic data (citations, papers, etc.)
✅ **Scalability**: Can handle millions of records
✅ **Django 5.2**: Full support with async features

### PostgreSQL Disadvantages
❌ **Setup Complexity**: Requires server installation/configuration
❌ **Resource Usage**: More memory/CPU overhead
❌ **Backup**: More complex than SQLite
❌ **WSL Considerations**: Need to manage PostgreSQL service

## Recommendation

### For Current Development Phase (Solo User)
**Stick with SQLite** if:
- You're still in active development/prototyping
- You're the only user
- You need fast iteration and easy reset
- You want minimal infrastructure

**Switch to PostgreSQL** if:
- You're planning to deploy soon
- You need full-text search for Scholar app
- You want production-like environment
- You're testing multi-user scenarios

### For Production Deployment
**Must use PostgreSQL** because:
- Multiple concurrent users
- Scholar app needs advanced search
- Data integrity is critical
- You'll need proper backups and replication

## My Recommendation for You

**Use PostgreSQL NOW** because:

1. **Scholar App Requirements**: Your SciTeX-Scholar will heavily benefit from PostgreSQL's full-text search
2. **Future-Proofing**: Easier to develop with production DB from start
3. **Django 5.2 Features**: Can leverage async PostgreSQL features
4. **Data Complexity**: Academic citations, papers, metadata benefit from PostgreSQL
5. **Migration Pain**: Better to switch now than migrate later with production data

## Implementation Plan

### Option 1: Keep Both (Recommended for Transition)
```python
# Development: SQLite (fast iteration)
# Staging: PostgreSQL (production-like testing)
# Production: PostgreSQL
```

### Option 2: Full PostgreSQL Switch
- Setup PostgreSQL in WSL
- Update settings to use PostgreSQL
- Migrate schema
- Test all functionality

## PostgreSQL Setup for WSL2

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo service postgresql start

# Create database and user
sudo -u postgres psql
CREATE DATABASE scitex_cloud_dev;
CREATE USER scitex_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_dev TO scitex_user;
ALTER DATABASE scitex_cloud_dev OWNER TO scitex_user;
\q

# Install Python driver
pip install psycopg2-binary
```

### Configuration
```python
# config/settings/settings_dev.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "scitex_cloud_dev",
        "USER": "scitex_user",
        "PASSWORD": "your_secure_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

## Final Recommendation

**Switch to PostgreSQL now** because:
- Your Scholar app is a core feature that needs advanced search
- You're already resetting the database (perfect timing!)
- Django 5.2 works better with PostgreSQL
- Avoid migration pain later

**Keep SQLite option** for:
- Quick local testing
- CI/CD pipelines
- Backup development environment

<!-- EOF -->
