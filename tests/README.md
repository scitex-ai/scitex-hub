# SciTeX Cloud Test Suite

## Directory Structure

```
tests/
│
├── unit/                         # Pure functions, no external dependencies
│   └── apps/                     # Python unit tests mirroring apps/
│       ├── core/
│       ├── project_app/
│       │   ├── utils/
│       │   └── services/
│       ├── scholar_app/
│       │   ├── utils/
│       │   └── services/
│       ├── figrecipe_app/
│       ├── writer_app/
│       ├── console_app/
│       └── ...
│
├── db/                           # Database tests (Django ORM, no HTTP)
│   └── apps/
│       ├── project_app/          # Model creation, validation, queries
│       │   ├── test_project_model.py
│       │   └── test_file_model.py
│       ├── scholar_app/
│       │   ├── test_library_model.py
│       │   └── test_citation_model.py
│       └── ...
│
├── api/                          # HTTP endpoint tests (uses DB)
│   └── apps/
│       ├── auth_app/
│       │   └── test_auth_endpoints.py
│       ├── project_app/
│       │   ├── test_project_crud.py
│       │   └── test_file_api.py
│       ├── scholar_app/
│       │   ├── test_search_api.py
│       │   └── test_bibtex_api.py
│       ├── figrecipe_app/
│       │   ├── test_gallery_api.py
│       │   └── test_bundle_api.py
│       └── ...
│
├── ui/                           # Browser-based tests (Playwright)
│   │
│   ├── components/               # Isolated UI widget tests
│   │   ├── panel_resizer/
│   │   │   ├── conftest.py
│   │   │   ├── test_toggle.py
│   │   │   ├── test_drag_resize.py
│   │   │   └── test_persistence.py
│   │   ├── file_tree/
│   │   │   ├── test_expand_collapse.py
│   │   │   ├── test_selection.py
│   │   │   └── test_drag_drop.py
│   │   ├── data_table/
│   │   └── shortcuts_modal/
│   │
│   ├── apps/                     # Single-app feature tests
│   │   ├── auth/
│   │   │   ├── test_login.py
│   │   │   ├── test_signup.py
│   │   │   └── test_password_reset.py
│   │   ├── project/
│   │   │   ├── test_create_project.py
│   │   │   ├── test_project_settings.py
│   │   │   └── test_file_operations.py
│   │   ├── scholar/
│   │   │   ├── test_search.py
│   │   │   ├── test_bibtex_upload.py
│   │   │   └── test_library.py
│   │   ├── vis/
│   │   │   ├── test_create_plot.py
│   │   │   ├── test_canvas_operations.py
│   │   │   └── test_export.py
│   │   ├── writer/
│   │   │   ├── test_editor.py
│   │   │   └── test_compilation.py
│   │   └── code/
│   │       ├── test_terminal.py
│   │       └── test_notebook.py
│   │
│   ├── cross_app/                # Multi-app workflow tests
│   │   ├── test_project_to_vis.py
│   │   ├── test_scholar_to_writer.py
│   │   └── test_full_paper_workflow.py
│   │
│   ├── conftest.py               # Shared Playwright fixtures
│   └── artifacts/                # Screenshots, videos (gitignored)
│
├── ts/                           # TypeScript unit tests (Vitest)
│   │
│   ├── shared/                   # Shared components tests
│   │   ├── components/
│   │   │   ├── workspace-files-tree/
│   │   │   ├── data-table/
│   │   │   └── media-editor/
│   │   ├── utils/
│   │   └── collaboration/
│   │
│   └── apps/                     # Per-app TypeScript tests
│       ├── figrecipe_app/
│       │   ├── vis/
│       │   │   ├── CanvasManager.test.ts
│       │   │   ├── PropertiesManager.test.ts
│       │   │   └── canvas/
│       │   └── vis-editor/
│       ├── scholar_app/
│       │   ├── search/
│       │   └── bibtex/
│       ├── writer_app/
│       │   ├── modules/
│       │   └── writer/
│       ├── console_app/
│       │   └── workspace/
│       └── project_app/
│
├── fixtures/                     # Shared test data
│   ├── users.json
│   ├── projects/
│   │   └── sample_project/
│   └── sample_files/
│       ├── sample.bib
│       └── sample.csv
│
├── conftest.py                   # Root pytest configuration
└── README.md                     # This file
```

---

## Test Categories

### Python Tests

| Category | Location | Dependencies | Speed | What to Test |
|----------|----------|--------------|-------|--------------|
| **Unit** | `unit/` | None | <1s | Pure functions, utilities, parsers, formatters |
| **DB** | `db/` | Django ORM | 1-5s | Models, validators, queries, constraints |
| **API** | `api/` | HTTP + DB | 1-10s | Endpoints, auth, permissions, responses |
| **UI** | `ui/` | Browser + Stack | 10-60s | User interactions, visual feedback |

### TypeScript Tests

| Category | Location | Dependencies | Speed | What to Test |
|----------|----------|--------------|-------|--------------|
| **Unit** | `ts/` | jsdom (Vitest) | <1s | Components, utilities, state, DOM manipulation |

### UI Test Subcategories

| Subcategory | Location | Scope | Example |
|-------------|----------|-------|---------|
| **Components** | `ui/components/` | Single widget | Panel resizer drag |
| **Apps** | `ui/apps/` | Single page/app | Create plot in Vis |
| **Cross-App** | `ui/cross_app/` | Multi-app workflow | Project → Vis → Export |

---

## Running Tests

### Setup (First Time)

```bash
# Install all test dependencies
make setup-testing            # Both Python and TypeScript

# Or individually
make setup-pytest             # Python: pytest + playwright
make setup-vitest             # TypeScript: vitest
```

### Quick Commands

```bash
# ─────────────────────────────────────────────────────────────
# Python Tests
# ─────────────────────────────────────────────────────────────

make test-unit                # Unit tests only (fastest)
make test-db                  # Database model tests
make test-api                 # API endpoint tests
make test-ui                  # UI tests (headless)
make test-ui-headed           # UI tests (visible browser)
make test-python              # All Python tests

# ─────────────────────────────────────────────────────────────
# TypeScript Tests
# ─────────────────────────────────────────────────────────────

make test-ts                  # Single run
make test-ts-watch            # Watch mode (re-run on change)
make test-ts-ui               # Visual Vitest UI
make test-ts-coverage         # With coverage report

# ─────────────────────────────────────────────────────────────
# All Tests
# ─────────────────────────────────────────────────────────────

make test-all                 # Everything (Python + TypeScript)
```

### Specific Tests

```bash
# By directory
pytest tests/unit/apps/scholar_app/ -v
pytest tests/api/apps/figrecipe_app/ -v
pytest tests/ui/apps/writer/ -v

# By file
pytest tests/ui/components/panel_resizer/test_toggle.py -v

# By test name
pytest -k "test_login" -v

# By marker
pytest -m "slow" -v           # Only slow tests
pytest -m "not slow" -v       # Skip slow tests

# TypeScript specific
npm run test:run -- tests/ts/figrecipe_app/
```

### Parallel Execution

```bash
# Python (pytest-xdist)
pytest tests/unit/ -n 4       # 4 parallel workers
pytest tests/ui/ -n 8         # 8 browser instances

# TypeScript (Vitest - parallel by default)
npm run test:run
```

---

## Writing Tests

### Python Unit Test

```python
# tests/unit/apps/scholar_app/utils/test_bibtex_parser.py

import pytest
from apps.scholar_app.utils.bibtex import parse_bibtex, ParseError


class TestBibtexParser:
    """Unit tests for BibTeX parsing utility."""

    def test_parse_valid_entry(self):
        """Parse a valid BibTeX entry."""
        bibtex = '@article{doe2023, author={Doe}, title={Test}}'
        result = parse_bibtex(bibtex)
        assert result['author'] == 'Doe'
        assert result['title'] == 'Test'

    def test_parse_invalid_entry_raises(self):
        """Invalid BibTeX raises ParseError."""
        with pytest.raises(ParseError):
            parse_bibtex('not valid bibtex')

    @pytest.mark.parametrize("entry_type", ["article", "book", "inproceedings"])
    def test_parse_different_types(self, entry_type):
        """Parse different entry types."""
        bibtex = f'@{entry_type}{{key, title={{Test}}}}'
        result = parse_bibtex(bibtex)
        assert result is not None
```

### Python DB Test

```python
# tests/db/apps/project_app/test_project_model.py

import pytest
from django.db import IntegrityError
from apps.project_app.models import Project


@pytest.mark.django_db
class TestProjectModel:
    """Database tests for Project model."""

    def test_create_project(self, user):
        """Create a project with valid data."""
        project = Project.objects.create(
            owner=user,
            name="Test Project",
            slug="test-project"
        )
        assert project.pk is not None
        assert project.slug == "test-project"

    def test_slug_auto_generated(self, user):
        """Slug is auto-generated from name if not provided."""
        project = Project.objects.create(owner=user, name="My Project")
        assert project.slug == "my-project"

    def test_duplicate_slug_raises(self, user):
        """Duplicate slug for same user raises IntegrityError."""
        Project.objects.create(owner=user, name="P1", slug="same")
        with pytest.raises(IntegrityError):
            Project.objects.create(owner=user, name="P2", slug="same")
```

### Python API Test

```python
# tests/api/apps/project_app/test_project_crud.py

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestProjectAPI:
    """API tests for project endpoints."""

    def test_create_project(self, authenticated_client):
        """POST /api/projects/ creates a project."""
        response = authenticated_client.post(
            reverse('api:project-list'),
            {'name': 'New Project'},
            content_type='application/json'
        )
        assert response.status_code == 201
        assert response.json()['name'] == 'New Project'

    def test_create_project_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.post(
            reverse('api:project-list'),
            {'name': 'Test'},
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_list_projects_returns_only_owned(self, authenticated_client, user):
        """List returns only projects owned by user."""
        response = authenticated_client.get(reverse('api:project-list'))
        assert response.status_code == 200
        for project in response.json():
            assert project['owner'] == user.username
```

### Python UI Test

```python
# tests/ui/apps/vis/test_create_plot.py

import pytest
from playwright.sync_api import Page
from scitex.browser import show_step, show_test_result, inject_visual_effects


class TestCreatePlot:
    """UI tests for plot creation in Vis app."""

    def test_create_line_plot_from_gallery(
        self, page: Page, logged_in_page, base_url: str
    ):
        """Create a line plot by selecting from gallery."""
        inject_visual_effects(page)

        # Step 1: Navigate to Vis
        show_step(page, 1, 5, "Opening Vis app...", "info")
        page.goto(f"{base_url}/vis/")
        page.wait_for_load_state("networkidle")

        # Step 2: Open gallery panel
        show_step(page, 2, 5, "Opening plot gallery...", "info")
        page.click("#gallery-button")
        page.wait_for_selector(".gallery-panel", state="visible")

        # Step 3: Select line plot category
        show_step(page, 3, 5, "Selecting line category...", "info")
        page.click("[data-category='line']")
        page.wait_for_timeout(300)

        # Step 4: Click on plot template
        show_step(page, 4, 5, "Selecting plot template...", "info")
        page.click("[data-plot-type='stx_line']")
        page.wait_for_timeout(1000)

        # Step 5: Verify plot created
        show_step(page, 5, 5, "Verifying plot on canvas...", "info")
        canvas_objects = page.locator(".canvas-object")
        assert canvas_objects.count() > 0, "No objects on canvas"

        show_test_result(page, True, "Line plot created successfully", delay_ms=2000)
```

### TypeScript Unit Test

```typescript
// tests/ts/figrecipe_app/vis/CanvasManager.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CanvasManager } from '@figrecipe_app/vis/CanvasManager';

describe('CanvasManager', () => {
    let manager: CanvasManager;

    beforeEach(() => {
        // Setup fresh instance
        manager = new CanvasManager({ width: 800, height: 600 });
    });

    afterEach(() => {
        // Cleanup
        manager.dispose();
    });

    describe('initialization', () => {
        it('should initialize with empty canvas', () => {
            expect(manager.getObjects()).toHaveLength(0);
        });

        it('should have correct dimensions', () => {
            expect(manager.getWidth()).toBe(800);
            expect(manager.getHeight()).toBe(600);
        });
    });

    describe('object management', () => {
        it('should add object to canvas', () => {
            const obj = { id: '1', type: 'rect', x: 0, y: 0 };
            manager.addObject(obj);
            expect(manager.getObjects()).toContain(obj);
        });

        it('should remove object from canvas', () => {
            const obj = { id: '1', type: 'rect', x: 0, y: 0 };
            manager.addObject(obj);
            manager.removeObject('1');
            expect(manager.getObjects()).not.toContain(obj);
        });

        it('should emit event on object add', () => {
            const callback = vi.fn();
            manager.on('objectAdded', callback);
            manager.addObject({ id: '1', type: 'rect' });
            expect(callback).toHaveBeenCalledOnce();
        });
    });
});
```

---

## UI Test Requirements

### Visual Feedback (Required)

All UI tests **must** provide visual feedback using `scitex.browser`:

```python
from scitex.browser import (
    inject_visual_effects,  # Enable visual effects
    show_step,              # Show step progress
    show_test_result,       # Show pass/fail result
    show_cursor_at,         # Show cursor position
    show_click_effect,      # Animate clicks
    highlight_element,      # Highlight elements
)

def test_something(page):
    inject_visual_effects(page)

    show_step(page, 1, 3, "Starting test...", "info")
    # ... test actions ...

    show_step(page, 2, 3, "Performing action...", "info")
    # ... more actions ...

    show_step(page, 3, 3, "Verifying result...", "success")
    # ... assertions ...

    show_test_result(page, True, "Test passed", delay_ms=2000)
```

### Failure Artifacts

On test failure, automatically captured:
- Screenshot (PNG)
- Console logs
- Page HTML

Location: `tests/ui/artifacts/{timestamp}/`

### Test File Size Limits

- **Maximum 150 lines** per test file
- **Maximum 5 tests** per file
- Group related tests in subdirectories

---

## Fixtures

### Python Fixtures (conftest.py)

```python
# tests/conftest.py - Available to all Python tests

@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user('testuser', 'test@test.com', 'password')

@pytest.fixture
def authenticated_client(client, user):
    """Django test client with logged-in user."""
    client.force_login(user)
    return client

@pytest.fixture
def project(user):
    """Create a test project."""
    from apps.project_app.models import Project
    return Project.objects.create(owner=user, name="Test Project")
```

```python
# tests/ui/conftest.py - UI tests only

@pytest.fixture
def base_url():
    """Base URL for the test server."""
    return "http://127.0.0.1:8000"

@pytest.fixture
def test_credentials():
    """Test user credentials from .env.dev."""
    return {"username": "test-user", "password": "Password123!"}

@pytest.fixture
def logged_in_page(page, base_url, test_credentials):
    """Playwright page with user already logged in."""
    login_user(page, base_url, test_credentials)
    return page
```

### TypeScript Setup (vitest.config.ts)

Path aliases configured:
```typescript
'@figrecipe_app'     → 'apps/figrecipe_app/static/figrecipe_app/ts'
'@scholar_app' → 'apps/scholar_app/static/scholar_app/ts'
'@writer_app'  → 'apps/writer_app/static/writer_app/ts'
'@console_app'    → 'apps/console_app/static/console_app/ts'
'@shared'      → 'static/shared/ts'
```

---

## Test Markers

```python
# Slow tests (skip with -m "not slow")
@pytest.mark.slow
def test_heavy_computation():
    ...

# Database required
@pytest.mark.django_db
def test_model_save():
    ...

# Skip in CI environment
@pytest.mark.skipci
def test_local_only():
    ...
```

Run by marker:
```bash
pytest -m "not slow"          # Skip slow tests
pytest -m "django_db"         # Only DB tests
```

---

## Coverage

```bash
# Python coverage
pytest tests/unit/ tests/db/ tests/api/ --cov=apps --cov-report=html
open htmlcov/index.html

# TypeScript coverage
npm run test:coverage
open coverage/ts/index.html
```

**Targets:**
- Unit tests: 80%+
- DB tests: Key models covered
- API tests: All endpoints covered
- UI tests: Critical user flows covered

---

## CI Integration

Tests run in order (fail-fast):

```
1. make test-unit        ─── Must pass (fast feedback)
2. make test-ts          ─── Must pass
3. make test-db          ─── Must pass
4. make test-api         ─── Must pass
5. make test-ui          ─── Run on PR merge to main
```

---

## Test Sync Scripts

Keep test files synchronized with source:

```bash
# Python: Sync tests/unit/ and tests/db/ with apps/
make sync-tests               # Create missing test stubs
make sync-tests-move          # Also move stale tests to .stale/

# TypeScript: Sync tests/ts/ with apps/*/static/*/ts/
make sync-ts-tests            # Create missing test stubs
make sync-ts-tests-move       # Also move stale tests to .stale/
```

---

## Troubleshooting

### Playwright browser not found
```bash
make setup-pytest
# or:
playwright install chromium
```

### TypeScript import errors
```bash
# Verify vitest config aliases
cat vitest.config.ts

# Rebuild if needed
npm run build
```

### Database tests failing
```bash
# Ensure migrations are applied
make ENV=dev migrate
```

### UI tests timing out
```bash
# Run with visible browser to debug
pytest tests/ui/path/to/test.py --headed --slowmo=500
```

### Test credentials not found
```bash
# Check .env.dev has test user credentials
grep TEST_USER SECRET/.env.dev
```
