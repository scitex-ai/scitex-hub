# Test Organization

## Directory Structure

```
tests/
├── conftest.py              # Root pytest config (shared fixtures)
├── pytest.ini               # Pytest settings (already exists at root)
│
├── unit/                    # Fast tests (no DB, no browser, no network)
│   ├── apps/                # Python unit tests (moved from tests/apps/)
│   │   └── <app_name>/      # Mirrors apps/<app_name>/ structure
│   └── ts/                  # TypeScript unit tests (moved from tests/ts/)
│       └── <app_name>/      # Mirrors apps/<app>/static/<app>/ts/
│
├── integration/             # Tests requiring DB/services (no browser)
│   └── apps/
│       └── <app_name>/
│
├── e2e/                     # Browser-based tests (Playwright)
│   ├── conftest.py          # E2E shared fixtures
│   ├── base.py              # Base test class with common patterns
│   ├── auth/                # Authentication workflows
│   ├── project/             # Project management
│   ├── scholar/             # Scholar app
│   ├── writer/              # Writer app
│   ├── code/                # Code app
│   ├── vis/                 # Vis app
│   └── shared/              # Cross-app components (panel_resizer, etc.)
│
├── fixtures/                # Shared test data
│   ├── users.json           # Test user configurations
│   ├── projects/            # Sample project data
│   └── files/               # Sample files for upload tests
│
└── artifacts/               # Generated test artifacts (gitignored)
    ├── screenshots/
    ├── videos/
    └── reports/
```

## Test Types & When to Use

| Type | Speed | Dependencies | Use For |
|------|-------|--------------|---------|
| **unit** | Fast (<1s) | None | Pure functions, utilities, data transforms |
| **integration** | Medium (1-10s) | DB, Django | Models, services, API endpoints |
| **e2e** | Slow (10-60s) | Browser, Full stack | User workflows, UI interactions |

## Running Tests

```bash
# All tests
make test-all

# By type
make test-unit            # Fast unit tests only
make test-integration     # Integration tests (requires DB)
make test-e2e             # E2E tests (requires running server)

# TypeScript
make test-ts              # Vitest unit tests
make test-ts-watch        # Watch mode

# Specific app
make test-app APP=scholar

# Specific test file
pytest tests/e2e/auth/test_login.py -v
```

## E2E Test Standards

### 1. Visual Feedback (Required)
All E2E tests must provide visual feedback using `scitex.browser`:

```python
from scitex.browser import show_step, show_test_result, inject_visual_effects

def test_something(page):
    inject_visual_effects(page)
    show_step(page, 1, 3, "Step description", "info")
    # ... test code ...
    show_test_result(page, True, "Test passed")
```

### 2. Test File Size
- Maximum 150 lines per test file
- Maximum 5 tests per file
- Group related tests in subdirectories

### 3. Naming Convention
```
test_<feature>_<scenario>.py
test_login.py
test_login_with_invalid_password.py
test_project_create.py
```

### 4. Required Fixtures
```python
@pytest.fixture
def logged_in_page(page, base_url, test_credentials):
    """Page with user already logged in."""
    login_user(page, base_url, test_credentials)
    return page
```

## Setup Scripts

```bash
# Install all test dependencies
make setup-testing

# Install specific
make setup-pytest         # Python testing (pytest + playwright)
make setup-vitest         # TypeScript testing (vitest)
```

## CI Integration

Tests run in this order:
1. `make test-unit` - Must pass (fast feedback)
2. `make test-ts` - Must pass
3. `make test-integration` - Must pass
4. `make test-e2e` - Run on merge to main

## Coverage Requirements

- Unit tests: 80% coverage target
- Integration: Key paths covered
- E2E: Critical user journeys covered
