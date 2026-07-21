#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database test configuration - Django ORM tests.

All tests in this directory require Django DB access.
Mark tests with @pytest.mark.django_db to enable database access.

Note: Do NOT call django.setup() at module level — pytest-django handles
this via DJANGO_SETTINGS_MODULE in pyproject.toml.  Module-level setup
causes collection errors when other tests leave mocks in place.
"""

import pytest


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )


@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
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
