#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_live_viewer_public_access.py
"""Regression tests: the public read-only live-paper viewer (scitex-hub#146
Part B) -- ``apps/infra/project_app/views/projects/live_viewer.py``.

WHAT THIS ROUTE IS
-------------------
``/<username>/<slug>/live/`` and ``/<username>/<slug>/live/v2/<endpoint>``
are the FIRST anonymous, unauthenticated entry point into
``scitex_writer._django``'s viewer -- every prior route
(``/apps/writer/{editor,viewer}-v2/``) is ``@login_required``
unconditionally. Reaching this module at all means an attacker (or a
misconfigured caller) needs no session whatsoever, so its default-deny
boundary and its working_dir override are the two properties this file
exists to pin down.

SCOPE OF THESE TESTS
---------------------
  * The visibility gate (``@project_access_required``) -- a PRIVATE or
    nonexistent project must 404, not merely redirect or 403 (a 403 would
    confirm the project exists to an anonymous caller).
  * The method gate on the API route -- non-GET must 405 BEFORE
    scitex-writer is even imported, so this holds even in an environment
    where scitex-writer is absent.
  * The ``_resolve_from_request_project`` resolver that feeds
    ``WorkingDirScopedView`` -- pure-function tests, no DB.
  * The working_dir override end-to-end, when scitex-writer IS installed
    (skipped otherwise via ``pytest.importorskip``) -- mirrors the property
    ``tests/security/test_writer_v2_working_dir_override.py`` proves for the
    authenticated route, exercised here through THIS route's own wiring.

One assertion per test (STX-TQ007).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.views.projects import live_viewer

pytestmark = [pytest.mark.security]


class TestResolveFromRequestProject:
    """Unit tests for the WorkingDirScopedView resolver. No DB, no scitex-writer."""

    def test_returns_resolved_path_from_request_project(self):
        # Arrange
        class _FakeProject:
            pk = 1

            def get_local_path(self):
                return Path("/tmp/some-live-project")

        class _Req:
            project = _FakeProject()

        # Act
        result = live_viewer._resolve_from_request_project(_Req())
        # Assert
        assert str(result) == "/tmp/some-live-project"

    def test_returns_none_when_request_has_no_project_attr(self):
        # Arrange
        class _Req:
            pass  # no .project at all

        # Act
        result = live_viewer._resolve_from_request_project(_Req())
        # Assert
        assert result is None

    def test_returns_none_when_get_local_path_raises(self):
        # Arrange
        class _FakeProject:
            pk = 1

            def get_local_path(self):
                raise RuntimeError("boom")

        class _Req:
            project = _FakeProject()

        # Act
        result = live_viewer._resolve_from_request_project(_Req())
        # Assert
        assert result is None


class LiveViewerAccessControlTest(TestCase):
    """Boundary checks reachable without scitex-writer installed."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="live-viewer-owner")
        cls.public_project = Project.objects.create(
            owner=cls.owner,
            name="Public Demo",
            slug="public-demo",
            visibility="public",
        )
        cls.private_project = Project.objects.create(
            owner=cls.owner,
            name="Private Demo",
            slug="private-demo",
            visibility="private",
        )

    def setUp(self):
        self.rf = RequestFactory()

    def test_private_project_viewer_404s_for_anonymous_caller(self):
        # Arrange
        request = self.rf.get("/live-viewer-owner/private-demo/live/")
        request.user = AnonymousUser()

        def call():
            return live_viewer.project_live_viewer(
                request, username="live-viewer-owner", slug="private-demo"
            )

        # Act / -- nothing to do before the assert; the call itself is the trigger
        # Assert
        with pytest.raises(Http404):
            call()

    def test_unknown_project_viewer_404s(self):
        # Arrange
        request = self.rf.get("/live-viewer-owner/does-not-exist/live/")
        request.user = AnonymousUser()

        def call():
            return live_viewer.project_live_viewer(
                request, username="live-viewer-owner", slug="does-not-exist"
            )

        # Act / -- nothing to do before the assert; the call itself is the trigger
        # Assert
        with pytest.raises(Http404):
            call()

    def test_api_endpoint_rejects_post_before_touching_scitex_writer(self):
        # Arrange: POST against a PUBLIC project -- only the method should matter.
        request = self.rf.post("/live-viewer-owner/public-demo/live/v2/api/claims")
        request.user = AnonymousUser()
        # Act
        response = live_viewer.project_live_viewer_api(
            request,
            username="live-viewer-owner",
            slug="public-demo",
            endpoint="api/claims",
        )
        # Assert
        assert response.status_code == 405

    def test_writer_not_installed_404s_for_public_project(self):
        # Arrange
        request = self.rf.get("/live-viewer-owner/public-demo/live/")
        request.user = AnonymousUser()
        original = live_viewer._writer_installed
        live_viewer._writer_installed = lambda: False

        def call():
            return live_viewer.project_live_viewer(
                request, username="live-viewer-owner", slug="public-demo"
            )

        # Act / -- nothing to do before the assert; the call itself is the trigger
        # Assert
        try:
            with pytest.raises(Http404):
                call()
        finally:
            live_viewer._writer_installed = original


class LiveViewerWorkingDirOverrideTest(TestCase):
    """Public project, scitex-writer present: the resolved working_dir always
    wins over whatever the caller supplies in ``?working_dir=``.
    """

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="live-viewer-owner2")
        cls.project = Project.objects.create(
            owner=cls.owner,
            name="Public Demo",
            slug="public-demo2",
            visibility="public",
            local_path="/srv/live-paper-demo",
        )

    def setUp(self):
        pytest.importorskip("scitex_writer", reason="scitex-writer not installed")

    def test_caller_supplied_working_dir_is_discarded(self):
        # Arrange: swap the real viewer_page for a spy that records what it saw.
        import scitex_writer._django.views as writer_views

        seen = {}

        def _spy_viewer_page(request):
            seen["working_dir"] = request.GET.get("working_dir")
            return HttpResponse("ok")

        original = writer_views.viewer_page
        writer_views.viewer_page = _spy_viewer_page
        request = RequestFactory().get(
            "/live-viewer-owner2/public-demo2/live/?working_dir=/etc/passwd"
        )
        request.user = AnonymousUser()
        # Act
        try:
            live_viewer.project_live_viewer(
                request, username="live-viewer-owner2", slug="public-demo2"
            )
        finally:
            writer_views.viewer_page = original
        # Assert
        assert seen["working_dir"] == "/srv/live-paper-demo"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
