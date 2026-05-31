#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-hub/tests/conftest.py

"""
Pytest configuration and shared fixtures for SciTeX test suite.

Provides:
- Django setup
- Test user credentials
- Database fixtures
- Common utilities
"""

import os
import sys
import sysconfig
import time
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Module-import-time coverage wiring (parallel + subprocess support).
#
# `os.environ.setdefault` would be a no-op here because pytest-cov has
# already set COVERAGE_FILE to a tmp dir by the time conftest is loaded.
# Force-set so child Python interpreters (subprocess.run, jupyter
# nbconvert --execute, …) record into the canonical repo-root shards.
# See scitex-dev/_skills/general/05_development_06_subprocess-coverage.md.
# ---------------------------------------------------------------------------
os.environ["COVERAGE_PROCESS_START"] = str(PROJECT_ROOT / "pyproject.toml")
os.environ["COVERAGE_FILE"] = str(PROJECT_ROOT / ".coverage")


def _ensure_subprocess_coverage_shim() -> None:
    """Drop an idempotent ``.pth`` file in site-packages that auto-starts
    coverage in every child Python interpreter via
    ``coverage.process_startup()``.
    """
    purelib = Path(sysconfig.get_paths()["purelib"])
    pth = purelib / "_scitex_hub_subprocess_coverage.pth"
    shim = (
        "import os, coverage\n"
        "if os.environ.get('COVERAGE_PROCESS_START'):\n"
        "    coverage.process_startup()\n"
    )
    try:
        if not pth.exists() or pth.read_text() != shim:
            pth.write_text(shim)
    except OSError:
        # site-packages may be read-only (e.g. system Python); silently
        # skip — local dev venvs are writable and that's where it matters.
        pass


_ensure_subprocess_coverage_shim()

# Ensure logs directory exists
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
os.environ["DJANGO_LOG_LEVEL"] = "ERROR"

# Load environment variables
from dotenv import load_dotenv

ENV_FILE = PROJECT_ROOT / "SECRET" / ".env.dev"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


# Setup Django (handle missing dependencies gracefully)
try:
    import django
    from django.conf import settings

    if hasattr(settings, "LOGGING"):
        settings.LOGGING = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"console": {"class": "logging.StreamHandler"}},
            "root": {"handlers": ["console"], "level": "ERROR"},
        }

    django.setup()
    DJANGO_AVAILABLE = True
except Exception as e:
    print(f"[conftest] Django setup skipped: {e}")
    DJANGO_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================

TEST_USER_USERNAME = os.getenv("SCITEX_HUB_TEST_USER_USERNAME", "test-user")
TEST_USER_PASSWORD = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD", "Password123!")
BASE_URL = os.getenv("SCITEX_BASE_URL", "http://127.0.0.1:8000")


# =============================================================================
# Session-scoped fixtures
# =============================================================================


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return BASE_URL


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials."""
    return {
        "username": TEST_USER_USERNAME,
        "password": TEST_USER_PASSWORD,
    }


# =============================================================================
# Function-scoped fixtures
# =============================================================================


@pytest.fixture
def timestamp():
    """Generate unique timestamp for test data."""
    return int(time.time() * 1000)


@pytest.fixture
def unique_username(timestamp):
    """Generate unique username for test."""
    return f"test_user_{timestamp}"


@pytest.fixture
def unique_email(timestamp):
    """Generate unique email for test."""
    return f"test_{timestamp}@example.com"


@pytest.fixture
def new_user_data(unique_username, unique_email):
    """Generate data for creating a new test user."""
    return {
        "username": unique_username,
        "email": unique_email,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
    }


# =============================================================================
# Database fixtures
# =============================================================================


@pytest.fixture
def django_user_model():
    """Get Django User model."""
    if not DJANGO_AVAILABLE:
        pytest.skip("Django not available")
    from django.contrib.auth import get_user_model

    return get_user_model()


@pytest.fixture
def create_test_user(django_user_model, new_user_data):
    """Create a test user in the database."""
    user = django_user_model.objects.create_user(
        username=new_user_data["username"],
        email=new_user_data["email"],
        password=new_user_data["password"],
    )
    yield user
    # Cleanup
    try:
        user.delete()
    except Exception:
        pass


# =============================================================================
# Cleanup fixtures
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_users():
    """Cleanup test users after all tests complete."""
    yield

    if not DJANGO_AVAILABLE:
        return

    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        deleted_count, _ = User.objects.filter(
            username__startswith="test_user_"
        ).delete()
        if deleted_count > 0:
            print(f"\n[Cleanup] Deleted {deleted_count} test user(s)")
    except Exception as e:
        print(f"\n[Cleanup] Skipped (DB not accessible): {e}")


# =============================================================================
# Headless release-gate guard
# =============================================================================
#
# The global ``addopts`` in pyproject.toml no longer carry the Playwright
# browser flags (``--browser``/``--headed``/``--slowmo``/``--video``/
# ``--screenshot``). That keeps the release gate (``pytest tests/ -x``, run by
# the pytest-matrix workflow in headless CI) from trying to launch a *headed*
# browser. But pytest-playwright still launches a (headless) browser whenever
# an E2E test that uses the ``page``/``browser`` fixtures is collected, so a
# plain ``pytest tests/`` would still open a browser at run time.
#
# The "E2E Mobile Tests" workflow (e2e-mobile.yml) drives the browser tests
# explicitly: it clears addopts with ``-o "addopts="`` and passes ``--browser``
# (plus ``--headed=false --screenshot --video``) on the command line. We detect
# that by checking whether ``--browser`` was supplied; when it was, the E2E
# tests run untouched. Otherwise (the headless gate) we skip everything under
# ``tests/e2e/`` and anything marked ``@pytest.mark.e2e``.


# Playwright fixtures that imply a real browser must be launched. Any test
# requesting one of these would call ``BrowserType.launch`` at run time, which
# crashes in the headless release gate where no browser executable is provided.
# pytest-playwright provides ``page``/``browser``/``context``/``browser_context``
# etc.; ``live_server`` (pytest-django) spins up a live HTTP server that these
# browser tests target. Detecting the fixture names lets us catch browser tests
# that live OUTSIDE ``tests/e2e/`` (e.g. ``tests/ui/...``) without having to mark
# every file by hand.
_BROWSER_FIXTURES = frozenset(
    {
        "page",
        "browser",
        "context",
        "browser_context",
        "browser_context_args",
        "browser_type",
        "browser_name",
        "new_context",
        "new_page",
        "live_server",
    }
)


def pytest_collection_modifyitems(config, items):
    """Skip E2E/browser tests in the headless gate; run them when the
    "E2E Mobile Tests" workflow passes ``--browser`` explicitly.

    A test is treated as a browser test (and skipped in the headless gate) when
    it lives under ``tests/e2e/``, is marked ``@pytest.mark.e2e``, OR requests a
    Playwright/live-server fixture (``page``, ``browser``, ``live_server``, …).
    The fixture check is what keeps a plain ``pytest tests/`` from launching a
    browser for the browser-driven tests under ``tests/ui/``.
    """
    browser_requested = False
    try:
        browser_requested = bool(config.getoption("--browser"))
    except (ValueError, KeyError):
        # pytest-playwright not installed → no --browser option → headless gate.
        browser_requested = False
    if browser_requested:
        return

    skip_e2e = pytest.mark.skip(
        reason="E2E/browser test skipped in headless gate "
        "(run via the 'E2E Mobile Tests' workflow with --browser)"
    )
    e2e_dir = os.sep + "e2e" + os.sep
    for item in items:
        path = str(getattr(item, "fspath", ""))
        uses_browser_fixture = bool(
            _BROWSER_FIXTURES.intersection(getattr(item, "fixturenames", ()))
        )
        if "e2e" in item.keywords or e2e_dir in path or uses_browser_fixture:
            item.add_marker(skip_e2e)
