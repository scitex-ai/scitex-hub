# SciTeX Cloud - Requirements & Configuration Review
**Date:** 2025-10-19
**Status:** Active Development

## Project Overview

**Live URL:** https://scitex.ai
**Development Status:** Active development, conceptual phase
**License:** MIT
**Contact:** Yusuke Watanabe (ywatanabe@alumni.u-tokyo.ac.jp)

---

## Python Dependencies

### Core Requirements
From `/deployment/requirements.txt`:

#### Django Stack (LTS)
- `Django==5.2.7` - Latest LTS version
- `djangorestframework==3.16.1` - REST API framework
- `django-cors-headers==4.9.0` - CORS handling
- `django-extensions==4.1` - Enhanced management commands
- `django-browser-reload==1.12.1` - Dev hot reload
- `djangorestframework-simplejwt==5.3.0` - JWT authentication

#### Database
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- Default fallback: SQLite3 (development)

#### Web Servers
- `gunicorn==21.2.0` - Production WSGI server
- `uwsgi` - Commented out (install separately with system packages)

#### Security
- `django-axes==6.3.0` - Brute-force protection
- `python-decouple==3.8` - Environment variable management
- `PyJWT==2.8.0` - JWT token handling
- `cryptography==42.0.5` - Encryption utilities

#### Integrations & APIs
- `requests>=2.31.0` - HTTP client

#### Utilities
- `python-dotenv==1.0.1` - Environment file support
- `whitenoise==6.11.0` - Static file serving

#### Development Tools
- `ipython==8.22.2` - Enhanced Python shell
- `django-debug-toolbar==6.0.0` - Debug interface

#### Monitoring
- `sentry-sdk==1.45.0` - Error tracking

#### Real-time Features
- `channels==4.3.1` - WebSocket support
- `channels-redis==4.3.0` - Redis channel layer

#### UI Utilities
- `django-widget-tweaks==1.5.0` - Form rendering enhancements

### External Modules (Commented Out)
The following are commented out but should be installed separately:
```python
# -e ./externals/impact_factor
# -e ./externals/SciTeX-Scholar
# -e ./externals/SciTeX-Code
# -e ./externals/SciTeX-Viz
# -e ./externals/SciTeX-Writer
```

---

## Django Configuration

### Settings Structure
Located in `/config/settings/`:
- `settings_shared.py` - Base shared settings
- `settings_dev.py` - Development overrides
- `settings_prod.py` - Production configuration

### Key Settings Highlights

#### Database Configuration
- **Development:** SQLite3 at `data/db/sqlite/scitex_cloud.db`
- **Production:** PostgreSQL (via SCITEX_CLOUD_POSTGRES_URL env var)

#### Cache & Sessions
- **Preferred:** Redis at `redis://127.0.0.1:6379/1`
- **Fallback:** Database cache (if Redis unavailable)
- Session timeout: 24 hours (86400 seconds)

#### Static & Media Files
```python
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

#### Authentication
```python
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/core/"  # Dashboard
LOGOUT_REDIRECT_URL = "/"
```

#### Email Configuration
- Host: `mail1030.onamae.ne.jp` (scitex.ai domain)
- Port: 587 (TLS)
- From: `agent@scitex.ai` (configurable via env)

#### REST API Configuration
- Authentication: Session + JWT
- Default permission: IsAuthenticated
- Pagination: 20 items per page
- Renderers: JSON + Browsable API

#### JWT Token Settings
- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days
- Token rotation: Enabled
- Blacklist after rotation: Enabled

#### WebSocket/Channels
- **ASGI application:** `config.asgi.application`
- **Channel layer:** Redis (fallback to in-memory)
- Redis URL: `redis://127.0.0.1:6379/2`

---

## Application Structure

### Installed Apps (Auto-Discovery)
The system automatically discovers apps in `./apps/` directory:

```python
def discover_local_apps():
    """Discover all Django apps in the apps directory."""
    # Scans ./apps/ for directories with apps.py or __init__.py
```

### Current Apps (from git status & structure)
```
apps/
├── auth_app/           # Authentication & user management
├── billing_app/        # Billing system
├── code_app/           # SciTeX-Code integration
├── workspace_app/           # Core platform (landing, dashboard, middleware)
├── doc_app/            # Document management
├── gitea_app/          # Gitea integration (NEW)
├── integrations_app/   # Third-party integrations
├── profile_app/        # User profiles & settings
├── project_app/        # Project management
├── scholar_app/        # SciTeX-Scholar integration
├── search_app/         # Unified search
├── social_app/         # Social features
├── viz_app/            # SciTeX-Viz integration
└── writer_app/         # SciTeX-Writer integration
```

### Middleware Stack
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.workspace_app.middleware.GuestSessionMiddleware",  # Custom
]
```

### Context Processors
```python
TEMPLATES[0]["OPTIONS"]["context_processors"] = [
    ...
    "apps.workspace_app.context_processors.project_context",  # Custom
]
```

---

## External Integrations

### SciTeX Ecosystem (via `./externals/`)
Symlinked external modules:

| Module | Target | Status |
|--------|--------|--------|
| `code` | `../../scitex_repo/src/scitex` | Symlink |
| `scholar` | `../../scitex_repo/src/scitex/scholar` | Symlink |
| `viz` | `../../../win/documents/SciTeX-Viz` | Symlink |
| `paper` | `../../neurovista/paper` | Symlink |
| `overleaf` | Local directory | Active |
| `impact_factor` | Local directory | Active |
| `SciTeX-Example-Research-Project` | Local directory | Template |

**Note:** External modules are **static** (no AI by default) but can be enhanced with AI agents.

### Third-Party Integrations
- **ORCID OAuth** (configured via env vars)
  - `ORCID_CLIENT_ID`
  - `ORCID_CLIENT_SECRET`
  - `ORCID_REDIRECT_URI`

---

## Environment Variables

### Required for Production
```bash
SCITEX_CLOUD_DJANGO_SECRET_KEY="your-secret-key"
DEBUG=False
SCITEX_CLOUD_ALLOWED_HOSTS="your-domain.com"
SCITEX_CLOUD_POSTGRES_URL="postgres://..."
```

### Email Configuration
```bash
SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS="agent@scitex.ai"
SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD="..."
```

### Redis (Optional)
```bash
SCITEX_CLOUD_REDIS_URL="redis://127.0.0.1:6379/1"
```

### Development Default
```bash
SCITEX_CLOUD_ENV=development
SCITEX_CLOUD_DJANGO_SECRET_KEY=dev-secret-key-123
```

---

## Directory Structure

Per `CLAUDE.md` guidelines:

```
scitex-cloud/
├── apps/           # Django apps (XXX_app format)
├── config/         # Settings, WSGI, ASGI, URLs
├── data/           # Persistent data (databases, user data)
├── deployment/     # Deployment configs (requirements, nginx, uwsgi)
├── docs/           # Documentation
├── externals/      # External SciTeX modules (static, pip packages)
├── logs/           # Log files
├── media/          # User-uploaded files
├── scripts/        # Management scripts
├── static/         # Static assets (CSS, JS, images)
├── staticfiles/    # Collected static files (for production)
├── templates/      # Base HTML templates
├── tests/          # Test files
└── tmp/            # Temporary files, cache
```

**Critical Rule:** Do NOT place files in project root - use subdirectories.

---

## Known Issues from Screenshots

### Critical Bugs
1. **`/projects` route:** 404 error - "No User matches the given query"
   - Location: `apps.project_app.user_urls.user_profile_wrapper`
   - Cause: User authentication wrapper failing for visitor users

2. **Authentication UX:** Login page shows both success and error messages simultaneously

### Access Control
- **Scholar:** Works without login ✓
- **Writer:** Requires login (redirects to login page)
- **Viz:** Requires login (redirects to login page)
- **Projects:** 404 error (needs fix)

---

## Development Workflow

### Quick Start
```bash
# Virtual environment
source .env/bin/activate  # or .env-3.11/bin/activate

# Database
python manage.py migrate
python manage.py collectstatic --noinput

# Development server
./server.sh start                    # Development mode
./server.sh start -m windows         # For Windows access
./server.sh start -m prod -d         # Production daemon
```

### Server Management
Script: `./scripts/server/scitex_server.sh` (symlinked to `./server.sh`)

Commands:
- `start` - Start server (dev/prod/windows modes)
- `stop` - Stop all processes
- `restart` - Restart server
- `status` - Show process status
- `logs` - View logs
- `clean` - Clean temp files
- `test` - Run tests
- `shell` - Open Django shell
- `migrate` - Run migrations
- `static` - Collect static files

---

## Testing

### Test Commands
```bash
# Via server script
./server.sh test

# Direct Django
python manage.py test

# Custom test script
./tests/run_tests.sh --debug
```

---

## Design Philosophy

### Project-Centric Architecture
Per `CLAUDE.md`:
- All features (scholar, code, viz, writer) should link to user/group projects
- Basic functionality should be available to visitor users
- No fake data - show real errors as alerts

### API Keys
Handled via user models through dashboard/settings (not hardcoded)

### Static External Modules
External tools under `./externals/` are static pip packages/shell scripts:
- No built-in AI integration
- AI enhancement happens through agent integration (e.g., Claude Code)
- Reduces degrees of freedom for predictable behavior

---

## Next Steps (Based on Build-Measure-Learn)

### Immediate Priorities
1. **Fix /projects routing error** (critical)
2. **Improve authentication UX** (error message handling)
3. **Define guest access policy** (which features work without login?)
4. **Set up analytics** (user engagement tracking)

### Infrastructure Needs
- [ ] Error monitoring (Sentry already in requirements)
- [ ] Analytics platform
- [ ] User feedback system
- [ ] Performance monitoring

### Feature Development
- [ ] Guest demo mode for Scholar
- [ ] Onboarding flow
- [ ] Project templates
- [ ] Improved project creation UX

---

## Notes

- **Redis dependency:** Optional but recommended for production (caching + channels)
- **PostgreSQL:** Required for production (SQLite for dev only)
- **External modules:** Symlinked from other repos (maintain separately)
- **Documentation status:** Some docs may be outdated (per README warning)

---

## References

- Main docs: `./docs/`
- CLAUDE.md: Project instructions for AI assistance
- README.md: Quick start guide
- BUILD_MEASURE_LEARN_ANALYSIS.md: Current iteration analysis
- Deployment configs: `./deployment/`

---

**Last Updated:** 2025-10-19
**Next Review:** After critical bug fixes
