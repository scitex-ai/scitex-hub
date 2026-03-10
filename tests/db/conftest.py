#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database test configuration - Django ORM tests.

All tests in this directory require Django DB access.
Mark tests with @pytest.mark.django_db to enable database access.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure Django is configured
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")

import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )


@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="AdminPassword123!",
    )


@pytest.fixture
def project(db, user):
    """Create a test project."""
    from apps.infra.project_app.models import Project

    return Project.objects.create(
        owner=user,
        name="Test Project",
        slug="test-project",
    )
