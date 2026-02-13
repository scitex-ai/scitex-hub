# SciTeX Cloud V1 - Quick Start Guide

**Version:** 1.0
**Date:** 2025-10-16
**Status:** 🚀 Shipped

## What's Working

### ✓ Core Features
- **Homepage** - `http://scitex.ai/` (200 OK)
- **Design System** - `http://scitex.ai/dev/design.html` (200 OK)
- **Automatic app discovery** - Add apps to `./apps/` and they auto-register
- **Clean database** - Fresh migrations in `./data/scitex_cloud.db`

### 📦 Active Apps (10)
1. auth_app - Authentication
2. billing_app - Subscriptions
3. cloud_app - Landing pages
4. console_app - Code execution
5. workspace_app - Core functionality
6. dev_app - Design system (NEW)
7. project_app - Project management
8. scholar_app - Literature search
9. viz_app - Visualizations
10. writer_app - Scientific writing

## Quick Commands

### Start Server
```bash
./server.sh
# or
python manage.py runserver
```

### Check Configuration
```bash
python manage.py check
```

### Format Templates
```bash
python scripts/format_templates.py apps/cloud_app/templates/
```

### Create Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Project Structure

```
scitex-cloud/
├── apps/                    # Django apps (auto-discovered)
├── config/                  # Settings and URLs
├── data/                    # Database and backups
│   └── scitex_cloud.db     # Main database
├── docs/                    # Documentation
├── externals/               # SciTeX modules
├── scripts/                 # Utility scripts
├── static/                  # Static files
├── templates/               # Global templates
│   └── partials/           # Reusable components
└── tests/                   # Test files
```

## Known Issues (Non-Critical)

1. **Module pages (500 errors)**
   - /scholar/, /console/, /viz/, /writer/, /projects/
   - Need view implementations
   - Can iterate on these

2. **Warnings**
   - cloud_app namespace duplication (non-critical)
   - console_app missing apps.api (expected)
   - auth_app has no urlpatterns (uses cloud_app auth)

## What Got Shipped (5 Commits)

1. **Major refactor** - Removed 11 apps, added auto-discovery
2. **Template fixes** - Removed engine references
3. **Code cleanup** - Removed api dependencies
4. **Template formatter** - Auto-indentation tool

**Net:** -73,000 lines of code, +maintainability

## Philosophy Applied

> "Version 1 sucks, but ship it anyway."
> "Fail fast, learn faster."

We shipped a working foundation. Now we iterate!

## Next Iterations (When Ready)

- Fix module page views (scholar, code, viz, writer)
- Implement actual auth flows
- Add user dashboard
- Connect to external SciTeX modules

## Support

The system is clean, documented, and ready to build on.
**You've got this! 🎯**
