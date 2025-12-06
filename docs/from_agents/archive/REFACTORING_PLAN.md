# SciTeX Cloud Refactoring Plan

## Current Issues

### 1. Apps Organization (21 apps!)
- **Too many apps** - 21 Django apps is excessive
- **Empty apps** - Several skeleton apps with no functionality
- **Poor separation** - Overlapping responsibilities
- **Root clutter** - Old apps in root (violates CLAUDE.md)

### 2. Templates Organization (26 template dirs!)
- **Duplicate templates** - `/templates/` AND `/apps/*/templates/`
- **Inconsistent structure** - Some in root, some in apps
- **No partials reuse** - Repeated code across templates
- **Commented-out files** - design_system.html entirely commented

### 3. Static Files
- **Multiple sources** - `/static/`, `/staticfiles/`, `/media/static/staticfiles/`
- **App-specific CSS scattered** - Some in `/static/css/`, some in `apps/*/static/`
- **Legacy files** - Archived but not cleaned up

### 4. Configuration
- **Duplicate settings** - Had 3 settings files (now cleaned)
- **Scripts scattered** - Now organized into dev/prod (✓ DONE)

## Recommended Django Apps Structure

### Core Platform (Keep - 5 apps)

```
apps/
├── workspace_app/              # Dashboard, shared utilities
├── auth_app/              # Authentication, user profiles
├── project_app/           # Project management (project-centric!)
├── cloud_app/             # Landing, marketing pages
└── api/                   # API endpoints (v1, v2)
```

### SciTeX Modules (Keep - 5 apps)

```
apps/
├── scholar_app/           # Literature management
├── writer_app/            # Scientific writing
├── code_app/              # Data analysis
├── viz_app/               # Visualizations
└── engine_app/            # Emacs integration
```

### Integration Apps (Consolidate - 2 apps)

```
apps/
├── integrations_app/      # MERGE: orcid_app, mendeley_app, github_app, reference_sync_app
└── collaboration_app/     # Real-time collaboration features
```

### Remove/Archive (9 apps)

```
DELETE or ARCHIVE:
├── ai_assistant_app/      # Redundant (use engine_app)
├── onboarding_app/        # Empty skeleton
├── monitoring_app/        # Empty skeleton
├── document_app/          # Merge into writer_app
├── billing_app/           # Not implemented
└── Empty root apps/       # ai_assistant, monitoring_app, onboarding_app (in root)
```

**Result: 21 apps → 12 apps (43% reduction)**

## Templates Organization

### Current Problems
```
/templates/                # Root templates (design_system.html, etc.)
/apps/cloud_app/templates/ # App templates
/apps/*/templates/         # 26 different template dirs!
```

### Recommended Structure

```
templates/
├── base.html              # Main base template
├── partials/              # Reusable components
│   ├── header.html
│   ├── footer.html
│   ├── navigation.html
│   └── alerts.html
├── layouts/               # Page layouts
│   ├── two_column.html
│   ├── full_width.html
│   └── dashboard.html
└── emails/                # Email templates
    ├── password_reset.html
    └── welcome.html

apps/
└── [app_name]/
    └── templates/
        └── [app_name]/    # App-specific templates only
            ├── index.html
            └── partials/  # App-specific partials
                └── [component].html
```

### Template Consolidation Rules

1. **Global templates** → `/templates/`
   - base.html
   - design_system.html
   - error pages (404, 500)

2. **Shared partials** → `/templates/partials/`
   - header, footer, nav
   - Common components

3. **App templates** → `/apps/[app]/templates/[app]/`
   - App-specific pages only
   - Follow namespace pattern

4. **Landing page partials** → `/apps/cloud_app/templates/cloud_app/landing_partials/`
   - Already done! ✓

## Reusable Code Organization

### Current Issues
- Business logic in views.py (too large)
- No service layer
- Utilities scattered
- No clear separation of concerns

### Recommended Structure

```
apps/
└── workspace_app/
    ├── services/          # Business logic layer
    │   ├── email_service.py
    │   ├── auth_service.py
    │   └── project_service.py
    ├── utils/             # Shared utilities
    │   ├── validators.py
    │   ├── decorators.py
    │   └── helpers.py
    ├── mixins/            # Reusable view mixins
    │   ├── auth_mixins.py
    │   └── permission_mixins.py
    └── middleware/        # Custom middleware
        └── ...

apps/
└── [app_name]/
    ├── models.py          # Database models
    ├── views.py           # View logic (thin!)
    ├── services.py        # Business logic (thick!)
    ├── serializers.py     # API serializers
    ├── forms.py           # Django forms
    ├── urls.py            # URL routing
    └── tests/             # Tests
        ├── test_models.py
        ├── test_views.py
        └── test_services.py
```

### Service Layer Pattern

**Before (Fat Views):**
```python
# views.py - 600 lines!
def forgot_password(request):
    # 50 lines of business logic mixed with view logic
```

**After (Thin Views, Fat Services):**
```python
# services.py
class AuthService:
    @staticmethod
    def send_password_reset(email):
        # All business logic here
        pass

# views.py - clean!
def forgot_password(request):
    email = request.data.get('email')
    AuthService.send_password_reset(email)
    return render(...)
```

## Refactoring Phases

### Phase 1: Immediate Cleanup (Week 1)
1. **Remove empty apps**
   - Delete: ai_assistant/, monitoring_app/, onboarding_app/ (in root)
   - Archive empty skeleton apps

2. **Fix templates**
   - Uncomment `/templates/design_system.html`
   - Consolidate duplicate templates
   - Move shared templates to `/templates/partials/`

3. **Static files** (Already done! ✓)
   - Organized CSS into base/, common/, components/, pages/
   - Moved app CSS to apps/*/static/

### Phase 2: Apps Consolidation (Week 2)
1. **Merge integration apps**
   ```
   apps/integrations_app/
   ├── orcid/
   ├── mendeley/
   ├── github/
   └── reference_sync/
   ```

2. **Merge document/writer**
   ```
   apps/writer_app/
   ├── documents/     # From document_app
   ├── collaboration/ # Real-time editing
   └── templates/
   ```

3. **Update INSTALLED_APPS** in settings

### Phase 3: Service Layer (Week 3)
1. **Create core services**
   ```
   apps/workspace_app/services/
   ├── __init__.py
   ├── email_service.py
   ├── auth_service.py
   ├── project_service.py
   └── storage_service.py
   ```

2. **Refactor views to use services**
   - Extract business logic from views
   - Move to appropriate service classes
   - Keep views thin (10-20 lines max)

3. **Add tests for services**

### Phase 4: Template Refactoring (Week 4)
1. **Create shared partials**
   ```
   templates/partials/
   ├── forms/
   │   ├── input_field.html
   │   ├── checkbox.html
   │   └── radio_group.html
   ├── cards/
   │   ├── module_card.html
   │   └── feature_card.html
   └── sections/
       ├── hero.html
       └── cta.html
   ```

2. **Refactor large templates**
   - Split 400+ line templates into partials
   - landing.html (✓ DONE)
   - Other large pages

3. **Remove duplicate templates**

## File Structure After Refactoring

```
scitex-cloud/
├── apps/                  # All Django apps
│   ├── workspace_app/          # Core functionality + services
│   ├── auth_app/          # Authentication
│   ├── project_app/       # Projects (project-centric!)
│   ├── cloud_app/         # Landing/marketing
│   ├── api/               # API endpoints
│   ├── scholar_app/       # Literature
│   ├── writer_app/        # Writing + documents
│   ├── code_app/          # Data analysis
│   ├── viz_app/           # Visualizations
│   ├── engine_app/        # Emacs integration
│   ├── integrations_app/  # External integrations
│   └── collaboration_app/ # Real-time features
│
├── config/                # Django configuration
│   ├── settings/          # Environment settings
│   │   ├── __init__.py    # Auto-detect
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── deployment/        # Deployment configs
│   │   ├── uwsgi/
│   │   └── nginx/
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/             # Global templates
│   ├── base.html
│   ├── partials/          # Shared components
│   ├── layouts/           # Page layouts
│   ├── emails/            # Email templates
│   └── errors/            # 404, 500, etc.
│
├── static/                # Static files
│   ├── css/
│   │   ├── base/          # Framework overrides
│   │   ├── common/        # Shared utilities
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page-specific
│   │   └── legacy/        # Archived
│   ├── js/
│   └── images/
│
├── scripts/               # Management scripts
│   ├── dev/               # Development
│   ├── prod/              # Production
│   └── utils/             # Utilities
│
├── tests/                 # Project-wide tests
├── docs/                  # Documentation
├── logs/                  # Log files
├── data/                  # Databases, user data
├── media/                 # User uploads
└── externals/             # SciTeX modules (Scholar, Code, Viz, Writer)
```

## Benefits

### Code Quality
- ✅ **Single responsibility** - Each app does one thing well
- ✅ **Thin views** - Business logic in services
- ✅ **Reusable code** - Shared utilities and services
- ✅ **Testable** - Service layer easy to test

### Maintainability
- ✅ **Easy to find** - Clear organization
- ✅ **Less duplication** - Shared partials
- ✅ **Consistent patterns** - Service layer pattern
- ✅ **Better docs** - Clear structure

### Performance
- ✅ **Fewer apps to load** - 21 → 12 apps
- ✅ **Cleaner imports** - Less circular dependencies
- ✅ **Faster tests** - Focused test structure

## Migration Strategy

### Step 1: Backup
```bash
git checkout -b refactor/project-structure
git add .
git commit -m "Backup before refactoring"
```

### Step 2: Remove Empty Apps
```bash
# Archive empty apps
mv ai_assistant monitoring_app onboarding_app docs/archive/empty-apps/
```

### Step 3: Merge Apps
```bash
# Create integrations_app
mkdir -p apps/integrations_app/{orcid,mendeley,github,reference_sync}
# Move code from individual apps
# Update imports
```

### Step 4: Refactor Templates
```bash
# Create partials structure
mkdir -p templates/{partials,layouts,emails,errors}
# Move shared templates
# Update {% include %} statements
```

### Step 5: Create Service Layer
```bash
# Create services
mkdir -p apps/workspace_app/services
# Extract business logic from views
# Add tests
```

### Step 6: Test Everything
```bash
python manage.py check
python manage.py test
./scripts/dev/server.sh
# Verify all pages work
```

### Step 7: Update Documentation
- Update CLAUDE.md with new structure
- Document service layer pattern
- Update developer guide

## Timeline

- **Week 1:** Immediate cleanup (empty apps, templates)
- **Week 2:** Apps consolidation
- **Week 3:** Service layer introduction
- **Week 4:** Template refactoring
- **Week 5:** Testing and documentation

## Success Metrics

- Apps: 21 → 12 (43% reduction)
- Template directories: 26 → ~15
- View file sizes: <200 lines each
- Code reuse: Shared services and partials
- Test coverage: >80%

## Next Steps

1. Review this plan
2. Approve refactoring approach
3. Start with Phase 1 (immediate cleanup)
4. Iterative implementation with testing

---

Generated: 2025-10-15
Author: Claude Code
Project: SciTeX Cloud
