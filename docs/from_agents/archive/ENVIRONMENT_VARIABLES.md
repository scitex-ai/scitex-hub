<!-- ---
!-- Timestamp: 2025-10-18 14:00:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/ENVIRONMENT_VARIABLES.md
!-- --- -->

# SciTeX Cloud Environment Variables

All SciTeX Cloud environment variables use the `SCITEX_CLOUD_` prefix for easy searchability.

## Database Configuration

### Development Database

**Switch to SQLite:**
```bash
export SCITEX_CLOUD_USE_SQLITE_DEV=1
```

**PostgreSQL Connection (defaults provided):**
```bash
export SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev        # default: scitex_cloud_dev
export SCITEX_CLOUD_DB_USER_DEV=scitex_dev              # default: scitex_dev
export SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025     # default: scitex_dev_2025
export SCITEX_CLOUD_DB_HOST_DEV=localhost               # default: localhost
export SCITEX_CLOUD_DB_PORT_DEV=5432                    # default: 5432
```

### Production Database

**Switch to SQLite:**
```bash
export SCITEX_CLOUD_USE_SQLITE_PROD=1
```

**PostgreSQL Connection (for production deployment):**
```bash
export SCITEX_CLOUD_DB_NAME_PROD=scitex_cloud_prod      # default: scitex_cloud_prod
export SCITEX_CLOUD_DB_USER_PROD=scitex_prod            # default: scitex_prod
export SCITEX_CLOUD_DB_PASSWORD_PROD=your_secure_pass   # REQUIRED for remote DB
export SCITEX_CLOUD_DB_HOST_PROD=your-db-host.com       # default: localhost
export SCITEX_CLOUD_DB_PORT_PROD=5432                   # default: 5432
```

## Email Configuration

From base settings (already configured):
```bash
export SCITEX_SENDER_GMAIL=your-email@gmail.com
export SCITEX_SENDER_GMAIL_PASSWORD=your-app-password
```

## Django Settings

```bash
export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_dev   # or settings_prod
export SCITEX_CLOUD_DJANGO_SECRET_KEY=your-secret-key-here
```

## Debugging

```bash
export SQL_DEBUG=1              # Enable SQL query logging
export DEBUG=1                  # Enable Django debug mode (dev only)
```

## Example: Development with PostgreSQL

```bash
# ~/.bashrc or project .env file
export SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025
export SCITEX_SENDER_GMAIL=ywata1989@gmail.com
export SCITEX_SENDER_GMAIL_PASSWORD=your-app-password
```

## Example: Development with SQLite

```bash
export SCITEX_CLOUD_USE_SQLITE_DEV=1
export SCITEX_SENDER_GMAIL=ywata1989@gmail.com
export SCITEX_SENDER_GMAIL_PASSWORD=your-app-password
```

## Example: Production Deployment

```bash
# Production server environment
export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_prod
export SCITEX_CLOUD_DJANGO_SECRET_KEY=your-very-secure-secret-key
export SCITEX_CLOUD_DB_PASSWORD_PROD=production-password
export SCITEX_CLOUD_DB_HOST_PROD=db.scitex.cloud
export SCITEX_SENDER_GMAIL=noreply@scitex.cloud
export SCITEX_SENDER_GMAIL_PASSWORD=production-email-password
```

## Naming Convention

All environment variables follow this pattern:

```
SCITEX_CLOUD_[COMPONENT]_[SETTING]_[ENV]
```

Examples:
- `SCITEX_CLOUD_DB_PASSWORD_DEV` - Database password for development
- `SCITEX_CLOUD_DB_HOST_PROD` - Database host for production
- `SCITEX_CLOUD_USE_SQLITE_DEV` - Use SQLite for development

## Searching Environment Variables

To find all SciTeX Cloud environment variables:

```bash
# In your shell
env | grep SCITEX_CLOUD

# In code
grep -r "SCITEX_CLOUD_" config/settings/

# In documentation
grep -r "SCITEX_CLOUD_" docs/
```

## Security Best Practices

1. **Never commit secrets to git**
   - Use `.env` files (add to `.gitignore`)
   - Use environment variables on servers
   - Use secret management tools in production

2. **Use strong passwords**
   ```bash
   # Generate secure password
   openssl rand -base64 32
   ```

3. **Rotate credentials regularly**
   - Change database passwords quarterly
   - Update API keys when compromised
   - Regenerate SCITEX_CLOUD_DJANGO_SECRET_KEY if exposed

4. **Separate dev and prod credentials**
   - Never use production credentials in development
   - Use different passwords for dev and prod databases

## .env File Template

Create a `.env` file in project root (add to `.gitignore`):

```bash
# .env - Development environment variables
# DO NOT COMMIT THIS FILE

# Django
SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_dev
SCITEX_CLOUD_DJANGO_SECRET_KEY=dev-secret-key-change-in-production

# Database (PostgreSQL)
SCITEX_CLOUD_DB_NAME_DEV=scitex_cloud_dev
SCITEX_CLOUD_DB_USER_DEV=scitex_dev
SCITEX_CLOUD_DB_PASSWORD_DEV=scitex_dev_2025
SCITEX_CLOUD_DB_HOST_DEV=localhost
SCITEX_CLOUD_DB_PORT_DEV=5432

# Or use SQLite instead
# SCITEX_CLOUD_USE_SQLITE_DEV=1

# Email
SCITEX_SENDER_GMAIL=your-email@gmail.com
SCITEX_SENDER_GMAIL_PASSWORD=your-app-password

# Debugging
SQL_DEBUG=0
```

Load it with:
```bash
export $(cat .env | xargs)
```

Or use `python-decouple` or `django-environ` packages.

<!-- EOF -->
