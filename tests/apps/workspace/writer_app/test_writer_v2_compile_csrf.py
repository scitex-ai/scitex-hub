#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_writer_v2_compile_csrf.py
"""A real browser compile POST to /apps/writer/v2/api/compile is not CSRF-403'd.

The hub wrapper dropped scitex-writer's @csrf_exempt on api_dispatch; the
writer's bundled frontend sends no CSRF token, so editor-v2 compile got 403.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class WriterV2CompileCsrfTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="csrf-owner", password=PASSWORD)
        # A missing directory keeps the writer from starting a real compile.
        cls.project = Project.objects.create(
            slug="csrf-study",
            owner=cls.owner,
            name="csrf-study",
            visibility="private",
            local_path="/nonexistent/scitex-hub-test/csrf-study",
        )
        cls.owner.profile.last_active_repository = cls.project
        cls.owner.profile.save(update_fields=["last_active_repository"])

    def test_owner_compile_post_is_not_csrf_rejected(self):
        # Arrange
        client = Client(enforce_csrf_checks=True)
        client.login(username="csrf-owner", password=PASSWORD)
        # Act
        response = client.post(
            "/apps/writer/v2/api/compile", data="{}", content_type="application/json"
        )
        # Assert
        assert response.status_code != 403, response.content


# EOF
