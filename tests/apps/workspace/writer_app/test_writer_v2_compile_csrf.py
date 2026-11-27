#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_writer_v2_compile_csrf.py
"""Compile POSTs at /apps/writer/api/compile follow the LEAF's CSRF decision.

The hub used to exempt the writer API from CSRF because the leaf's bundled
frontend sent no token. Since scitex-writer 2.44.5 (the hub's floor) the
frontend sends ``X-CSRFToken`` on every write, so the generic plugin mount
keeps the leaf's ``csrf_protect``: a token-bearing browser POST is accepted
by the CSRF layer, a token-less cross-site one is refused.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret
COMPILE = "/apps/writer/api/compile"


class WriterCompileCsrfTest(TestCase):
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

    def _client(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="csrf-owner", password=PASSWORD)
        return client

    def test_compile_post_with_the_session_token_is_not_csrf_rejected(self):
        # Arrange — any rendered form page sets the session CSRF cookie
        client = self._client()
        client.get("/auth/login/")
        token = client.cookies["csrftoken"].value
        # Act
        response = client.post(
            COMPILE, data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=token
        )
        # Assert
        assert response.status_code != 403, response.content

    def test_compile_post_without_a_token_is_csrf_rejected(self):
        # Arrange
        client = self._client()
        # Act
        response = client.post(COMPILE, data="{}", content_type="application/json")
        # Assert
        assert response.status_code == 403


# EOF
