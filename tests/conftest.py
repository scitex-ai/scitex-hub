#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/conftest.py

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
import time
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

TEST_USER_USERNAME = os.getenv("SCITEX_CLOUD_TEST_USER_USERNAME", "test-user")
TEST_USER_PASSWORD = os.getenv("SCITEX_CLOUD_TEST_USER_PASSWORD", "Password123!")
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
