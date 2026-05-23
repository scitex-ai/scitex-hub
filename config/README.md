<!-- ---
!-- Timestamp: 2025-10-18 21:32:16
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/config/README.md
!-- --- -->

# SciTeX Hub Configuration

This directory contains all Django configuration files organized for easy environment management.

## Directory Structure

```
config/
├── settings/                      # Django settings (organized by environment)
│   ├── __init__.py               # Auto-detects environment
│   ├── settings_shared.py        # Shared settings for all environments
│   ├── settings_dev.py           # Development-specific settings
│   └── settings_prod.py          # Production-specific settings
├── asgi.py                       # ASGI application
├── wsgi.py                       # WSGI application
├── urls.py                       # URL configuration
├── routing.py                    # WebSocket routing
└── logger.py                     # Logging configuration
```

> **Note**: This directory contains **Django application configuration only**.
> For deployment configs (Nginx, uWSGI, PostgreSQL), see `../deployment/`

## Settings Files

### `settings_shared.py`
- Shared settings for all environments
- Database configuration (supports both PostgreSQL and SQLite)
- Installed apps
- Middleware
- Static/media files base configuration
- Logging setup

### `settings_dev.py`
- Imports from `settings_shared.py`
- DEBUG=True
- Development database (PostgreSQL `scitex_hub_dev` or SQLite fallback)
- CORS enabled for all origins
- Console logging
- Environment variables with `_DEV` suffix

### `settings_prod.py`
- Imports from `settings_shared.py`
- DEBUG=False
- Production database (PostgreSQL `scitex_hub_prod`)
- Security settings enforced
- HTTPS required
- Environment variables with `_PROD` suffix

## Environment Switching

### Method 1: Django Settings Module (Recommended)

```bash
# Development (default)
export SCITEX_HUB_DJANGO_SETTINGS_MODULE=config.settings.settings_dev
python manage.py runserver

# Production
export SCITEX_HUB_DJANGO_SETTINGS_MODULE=config.settings.settings_prod
```

### Method 2: Auto-detection

The `settings/__init__.py` automatically detects the environment based on:
- Hostname patterns
- Environment variables
- Working directory location

## Environment Variables

Both environments use `SCITEX_HUB_*` prefix:

**Development:**
```bash
SCITEX_HUB_DB_NAME_DEV=scitex_hub_dev
SCITEX_HUB_DB_USER_DEV=scitex_dev
SCITEX_HUB_DB_PASSWORD_DEV=scitex_dev_2025
```

**Production:**
```bash
SCITEX_HUB_DB_NAME_PROD=scitex_hub_prod
SCITEX_HUB_DB_USER_PROD=scitex_prod
SCITEX_HUB_DB_PASSWORD_PROD=your_secure_password
```

See `../deployment/docs/01_ENVIRONMENT_VARIABLES.md` for complete documentation.

## Deployment

For server deployment configuration (Nginx, uWSGI, systemd), see:
- **`../deployment/`** - Complete deployment configuration and documentation
  - `deployment/docs/00_QUICK_START.md` - Step-by-step deployment guide
  - `deployment/nginx/` - Nginx web server configs
  - `deployment/uwsgi/` - uWSGI application server configs
  - `deployment/postgres/` - PostgreSQL database setup

## See Also

- `../deployment/` - Server deployment configurations
- `../scripts/` - Database and deployment automation scripts
- `../apps/` - Django applications
