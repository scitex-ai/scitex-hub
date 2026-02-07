# SciTeX Apps Architecture

Standard directory structure for SciTeX Django applications.

## Standard App Structure

Each app should follow this modular organization:

```
{app_name}_app/
├── 📁 models/                  # Database models (split by domain)
│   ├── __init__.py            # Central export point for all models
│   ├── core.py                # Core domain models
│   ├── search.py              # Search/query models
│   ├── library.py             # User library/collection models
│   ├── collaboration.py       # Collaboration/sharing models
│   ├── integration.py         # Integration-specific models
│   └── repository.py          # Repository/data management models
│
├── 📁 views/                  # View logic organized by feature
│   ├── __init__.py            # Central export point
│   ├── search_views.py        # Search/discovery features
│   ├── library_views.py       # Library management
│   ├── export_views.py        # Export/download features
│   ├── collaboration_views.py # Sharing/collaboration
│   ├── annotation_views.py    # Annotations/comments
│   ├── workspace_views.py     # Workspace management
│   ├── project_views.py       # Project-specific views
│   ├── api_views.py           # API endpoints
│   └── trending_views.py      # Analytics/trending
│
├── 📁 services/               # Business logic (domain services)
│   ├── __init__.py            # Central export point
│   ├── service_name.py        # Domain-specific service
│   └── utils.py               # Shared utilities
│
├── 📁 integrations/           # External integrations
│   ├── __init__.py
│   ├── external_api.py        # Integration with external services
│   └── sync_service.py        # Data synchronization
│
├── 📁 templates/              # HTML templates
│   └── {app_name}/
│       ├── {app_name}_base.html      # Base template with {app_name} prefix
│       ├── {feature}.html            # Feature-specific templates
│       └── partials/
│           └── {component}.html      # Reusable components
│
├── 📁 static/                 # Static assets
│   └── {app_name}/
│       ├── css/
│       │   └── {app_name}.css        # Styles with {app_name} prefix
│       ├── js/
│       │   └── {app_name}.js         # Scripts with {app_name} prefix
│       └── images/
│           └── {icon_name}.svg       # Icons/images
│
├── 📁 legacy/                 # Archived code (old implementations)
│   ├── models_old.py          # Previous models.py
│   ├── simple_views.py        # Monolithic views
│   └── {archived_file}.py     # Other archived files
│
├── admin.py                   # Django admin configuration
├── apps.py                    # App configuration
├── forms.py                   # Django forms
├── signals.py                 # Django signals
├── urls.py                    # URL routing
├── tests.py                   # Unit tests
├── MODELS_REORGANIZATION.md   # (optional) Documentation of model organization
└── README.md                  # (optional) App-specific documentation


# Key Principles

## 1. Models Organization

**Split models.py into domain modules:**
- **core.py**: Entity definitions (e.g., Author, Journal, SearchIndex)
- **search.py**: Search/query-related models
- **library.py**: User library, collections, organization
- **collaboration.py**: Annotations, sharing, group models
- **integration.py**: Integration-specific models
- **repository.py**: Data repository, datasets, syncing

**Use string references to avoid circular imports:**
```python
# Instead of: ForeignKey(SearchIndex, ...)
# Use: ForeignKey('SearchIndex', ...)
related_papers = models.ManyToManyField('SearchIndex', related_name='associated_datasets')
external_model = models.ForeignKey('other_app.Model', on_delete=models.CASCADE)
```

**Central export in models/__init__.py:**
```python
from .core import Author, Journal, SearchIndex
from .search import SearchQuery, SearchResult
from .library import Collection, UserLibrary
# ... import all models

__all__ = [
    'Author', 'Journal', 'SearchIndex',
    'SearchQuery', 'SearchResult',
    'Collection', 'UserLibrary',
    # ... all models
]
```

Then import anywhere as:
```python
from apps.{app_name}.models import SearchIndex, Collection
```

## 2. Views Organization

**Organize views by feature, not by pattern:**
- Each view module handles a complete feature (search, library, export, etc.)
- Keep related views together
- Each module should be ~1000-2000 lines maximum
- Use `views/__init__.py` to export common views

**View module structure:**
```python
# apps/scholar_app/views/search_views.py
from django.shortcuts import render
from ..models import SearchIndex, SearchQuery
from ..services import search_service

def search(request):
    """Main search view"""
    pass

def search_filters(request):
    """Search filters sub-view"""
    pass

def search_results(request):
    """Results display sub-view"""
    pass
```

## 3. Services Organization

**Business logic should go in services, not views:**
- Views handle HTTP request/response
- Services handle business logic
- Services can be imported by other services, views, or management commands
- Keep services stateless (dependency injection preferred)

**Example service structure:**
```python
# apps/scholar_app/services/search_service.py
class SearchService:
    @staticmethod
    def search_papers(query, filters=None):
        """Business logic for searching papers"""
        pass

    @staticmethod
    def rank_results(papers):
        """Rank search results by relevance"""
        pass
```

## 4. Templates Naming Convention

**Use app-name prefix for base templates:**
- Base template: `{app_name}_base.html` (e.g., `scholar_app_base.html`)
- This prevents naming conflicts across apps
- Feature templates can be more descriptive: `feature_name.html`

**Example:**
```
templates/scholar_app/
├── scholar_app_base.html      # ✅ Prefixed base template
├── search.html                 # Feature template
├── library.html
├── export.html
└── partials/
    ├── search_card.html
    ├── paper_item.html
    └── filters.html
```

## 5. Static Files Naming Convention

**Use app-name prefix for CSS and JS files:**
- CSS: `{app_name}.css`
- JS: `{app_name}.js`
- This prevents file conflicts in collected static files

**Example:**
```
static/scholar_app/
├── css/
│   └── scholar_app.css        # ✅ Prefixed stylesheet
├── js/
│   └── scholar_app.js         # ✅ Prefixed script
└── images/
    ├── search_icon.svg
    └── collection_icon.svg
```

## 6. Legacy Code Handling

**When reorganizing an app:**
1. Create a `legacy/` directory
2. Move old files there (models_old.py, simple_views.py, etc.)
3. Keep legacy code for reference but don't import from it
4. Document what was archived and why

**Example legacy structure:**
```
legacy/
├── models_old.py        # Original 1432-line models.py
├── simple_views.py      # Monolithic views
├── views_advanced.py    # Complex view logic
└── README.md           # What was archived and when
```

## 7. Testing

**Each app should have a tests.py (or tests/ directory):**
- Unit tests for models
- View tests for HTTP endpoints
- Service tests for business logic
- Aim for 80%+ coverage on critical paths

## 8. Forward References in Django Models

**Use string references to avoid import-time issues:**

```python
# ✅ Good - avoids circular imports
class SearchResult(models.Model):
    search_index = models.ForeignKey('SearchIndex', on_delete=models.CASCADE)
    search_query = models.ForeignKey('SearchQuery', on_delete=models.CASCADE)
    collection = models.ForeignKey('Collection', on_delete=models.SET_NULL, null=True)

# ❌ Avoid - can cause circular import issues
from .core import SearchIndex  # May fail if SearchIndex imports SearchResult
class SearchResult(models.Model):
    search_index = models.ForeignKey(SearchIndex, on_delete=models.CASCADE)
```

## Current App Status

| App | Status | Notes |
|-----|--------|-------|
| scholar_app | ✅ Reorganized | Reference implementation (26 models organized into 6 modules, 9 view modules) |
| workspace_app | 🔄 In Progress | 707 lines, 9 models - Can follow scholar_app pattern |
| writer_app | ⏳ Pending | 1,503 lines, 20 models - Highest priority for reorganization |
| console_app | ⏳ Pending | 5 models, 297 lines - Needs query optimization |
| integrations_app | ⏳ Pending | Needs query optimization |
| profile_app | ⏳ Pending | Needs query optimization |
| search_app | ⏳ Pending | Needs query optimization |
| social_app | ⏳ Pending | Needs query optimization |
| viz_app | ⏳ Pending | 13 models, 408 lines - Monitor for growth |
| Other apps | ✅ Stable | < 5 models each, adequate organization |

## Quick Wins (Recommended Next Steps)

1. **Add Query Optimization** (5 apps - low effort, high impact)
   - Add `select_related()` and `prefetch_related()` to QuerySets
   - Reduces database queries significantly
   - Apps: console_app, integrations_app, profile_app, search_app, social_app

2. **Add Test Coverage** (5 apps - critical)
   - Each app should have tests.py with unit/view/service tests
   - Target 80%+ coverage on critical paths
   - Same 5 apps listed above

3. **Background Task Migration** (writer_app)
   - Move LaTeX compilation to Celery task queue
   - 5 TODOs identified
   - Improves response time significantly

## References

- Apps using this structure: `scholar_app` (reference implementation)
- Documentation: See `MODELS_REORGANIZATION.md` in `scholar_app/`
- Bulletin board: See `project_management/BULLETIN_BOARD.md`

---

**Last Updated:** 2025-10-23
**Architecture Version:** 1.0
