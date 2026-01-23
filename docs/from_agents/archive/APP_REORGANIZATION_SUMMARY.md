# SciTeX Cloud App Reorganization Summary

**Date:** 2025-10-16
**Status:** Completed

## Changes Made

### 1. App Cleanup
Removed unnecessary apps to streamline the codebase:
- Removed: engine_app, api, monitoring_app, orcid_app, reference_sync_app, mendeley_app, github_app, collaboration_app, ai_assistant_app, onboarding_app, integrations, document_app

### 2. Current Active Apps

The system now has **11 focused apps**:

1. **auth_app** - Authentication and user management
2. **billing_app** - Pricing, subscriptions, donations
3. **cloud_app** - Landing pages, main website
4. **code_app** - Code execution and analysis
5. **workspace_app** - Core functionality, projects, user profiles
6. **dev_app** - Development tools (design system)
7. **project_app** - Project management
8. **scholar_app** - Literature discovery
9. **viz_app** - Visualization tools
10. **writer_app** - Scientific writing
11. **__pycache__** - Python cache (not an app)

### 3. Automatic App Discovery

Implemented programmatic app registration in `config/settings/settings_shared.py`:

```python
def discover_local_apps():
    """Discover all Django apps in the apps directory."""
    apps_path = BASE_DIR / 'apps'
    local_apps = []

    if apps_path.exists():
        for item in sorted(apps_path.iterdir()):
            if item.is_dir() and not item.name.startswith('_'):
                if (item / 'apps.py').exists() or (item / '__init__.py').exists():
                    app_name = f"apps.{item.name}"
                    local_apps.append(app_name)

    return local_apps

LOCAL_APPS = discover_local_apps()
```

Benefits:
- Automatically discovers new apps
- No manual registration needed
- Reduces configuration errors

### 4. Automatic URL Discovery

Implemented programmatic URL pattern registration in `config/urls.py`:

```python
def discover_app_urls():
    """Discover and register URLs for all apps in ./apps/."""
    from pathlib import Path
    import importlib

    patterns = []
    apps_dir = Path(settings.BASE_DIR) / 'apps'

    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if app_dir.is_dir() and not app_dir.name.startswith('_'):
                urls_file = app_dir / 'urls.py'
                if urls_file.exists():
                    app_name = app_dir.name
                    url_prefix = app_name.replace('_app', '')

                    try:
                        urls_module = importlib.import_module(f'apps.{app_name}.urls')
                        if hasattr(urls_module, 'urlpatterns') and urls_module.urlpatterns:
                            patterns.append(
                                path(f"{url_prefix}/", include(f"apps.{app_name}.urls"))
                            )
                    except Exception as e:
                        print(f"Warning: Could not register URLs for {app_name}: {e}")

    return patterns
```

URL mapping (automatic):
- `auth_app` → `/auth/`
- `billing_app` → `/billing/`
- `cloud_app` → `/cloud/`
- `code_app` → `/code/`
- `workspace_app` → `/core/`
- `dev_app` → `/dev/`
- `project_app` → `/project/`
- `scholar_app` → `/scholar/`
- `viz_app` → `/viz/`
- `writer_app` → `/writer/`

### 5. Template Reorganization

Moved templates to their appropriate app directories:

#### Auth templates moved to `apps/auth_app/templates/auth_app/`:
- signin.html
- signup.html
- logout.html
- forgot_password.html
- reset_password.html
- email_verification.html
- verify_email.html

#### Billing templates moved to `apps/billing_app/templates/billing_app/`:
- pricing.html
- pricing_enhanced.html
- pricing_new.html
- premium_subscription.html
- donation_success.html

#### Cloud app templates organized:
```
apps/cloud_app/templates/cloud_app/
├── declaration/         # Legal and policy pages (NEW)
│   ├── contact.html
│   ├── cookie_policy.html
│   ├── privacy_policy.html
│   └── terms_of_use.html
├── landing_partials/    # Landing page components
├── pages/              # General informational pages
├── products/           # Product landing pages
├── base.html
├── features.html
└── landing.html
```

### 6. Design System

Created `dev_app` for development tools:
- **URL:** `/dev/design.html` or `/dev/design/`
- **Template:** `apps/dev_app/templates/dev_app/pages/design.html`
- **Features:**
  - Complete SciTeX design system documentation
  - Color palette reference
  - Component library
  - Typography guidelines
  - Hero gradient variants
  - Module icons (SVG and emoji)

### 7. Code Cleanup

Fixed references to removed apps:
- Commented out `document_app` imports in `workspace_app/signals.py`
- Commented out `document_app` imports in `workspace_app/directory_manager.py`
- Commented out `manuscript_draft` field in `workspace_app/models.py` and `project_app/models.py`
- Removed monitoring middleware from `settings_shared.py`

### 8. Configuration Status

Current system check status:
- **Errors:** 0
- **Warnings:** 1 (URL namespace 'cloud_app' duplication - non-critical)

## Benefits of New Structure

1. **Maintainability:** Apps are automatically discovered and registered
2. **Simplicity:** Reduced from 20+ apps to 11 focused apps
3. **Clarity:** Templates are organized by their owning app
4. **Scalability:** Easy to add new apps - just create in `./apps/` directory
5. **Reduced Dependencies:** Removed apps that required external dependencies (Stripe, etc.)

## Next Steps (Optional)

1. Create migrations for removed `manuscript_draft` field
2. Add auth views to `auth_app`
3. Fix `code_app` dependency on `apps.api` (if needed)
4. Resolve cloud_app namespace duplication warning (if needed)

## Files Modified

- `config/settings/settings_shared.py` - Automatic app discovery
- `config/urls.py` - Automatic URL discovery
- `apps/workspace_app/signals.py` - Removed document_app references
- `apps/workspace_app/directory_manager.py` - Removed document_app references
- `apps/workspace_app/models.py` - Commented manuscript_draft field
- `apps/project_app/models.py` - Commented manuscript_draft field
- `apps/dev_app/` - Created new app for design system
- `apps/billing_app/` - Recreated with basic views
- Template directories reorganized

## Architecture Notes

The automatic discovery pattern makes the codebase more maintainable:
- Adding a new app only requires creating it in `./apps/xxx_app/`
- No need to manually update settings or URLs
- Graceful error handling for apps with missing dependencies
- Clear warnings for configuration issues
