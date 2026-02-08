#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Management Tests

Test project creation, listing, and basic operations.
Requires authenticated session.

Priority: HIGH
Run time: < 120 seconds
"""

import re
import time

import pytest
import requests


def _fresh_session():
    """Create a fresh requests session for isolated tests."""
    s = requests.Session()
    s.verify = False
    s.timeout = 30
    return s


def _get_csrf(session, url):
    """Get CSRF token from a form page. Returns (response, csrf_token) or skips."""
    resp = session.get(url)
    assert resp.status_code == 200
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
    if not csrf_match:
        pytest.skip("Cannot extract CSRF token from form page")
    return resp, csrf_match.group(1)


class TestProjectList:
    """Test project listing functionality."""

    def test_user_profile_public(self, base_url, test_credentials):
        """User profile page is publicly accessible (GitHub-style)."""
        session = _fresh_session()
        username = test_credentials["username"]
        resp = session.get(f"{base_url}/{username}/", allow_redirects=False)
        # User profiles are public (like GitHub)
        assert resp.status_code == 200
        session.close()

    def test_new_project_requires_auth(self, base_url):
        """/new/ requires authentication."""
        session = _fresh_session()
        resp = session.get(f"{base_url}/new/", allow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "login" in location.lower()
        session.close()


class TestProjectCreate:
    """Test project creation flow."""

    def test_new_project_page_requires_auth(self, base_url):
        """/new/ page requires authentication (fresh session)."""
        session = _fresh_session()
        resp = session.get(f"{base_url}/new/", allow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "login" in location.lower()
        session.close()

    def test_new_project_landing_page(self, authenticated_session, base_url):
        """Project creation landing page loads with card options."""
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200
        # /new/ is a card-based landing page with creation options
        text = resp.text.lower()
        assert any(
            x in text for x in ["create", "blank", "template", "import", "new"]
        ), "Landing page should show project creation options"

    def test_blank_project_form_loads(self, authenticated_session, base_url):
        """Blank project creation form loads with expected fields."""
        resp = authenticated_session.get(f"{base_url}/new/?type=blank")
        assert resp.status_code == 200
        assert "csrfmiddlewaretoken" in resp.text
        assert "name" in resp.text.lower()

    def test_template_project_form_loads(self, authenticated_session, base_url):
        """Template project creation form loads with template options."""
        resp = authenticated_session.get(f"{base_url}/new/?type=template")
        assert resp.status_code == 200
        assert "csrfmiddlewaretoken" in resp.text
        assert "template" in resp.text.lower()

    def test_project_name_check_api(self, authenticated_session, base_url):
        """Project name availability check API works."""
        resp = authenticated_session.get(
            f"{base_url}/project/api/check-name/",
            params={"name": "test-unique-name-12345"},
        )
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data = resp.json()
            assert "available" in data or "valid" in data or "error" in data

    def test_create_blank_project(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a blank project successfully."""
        form_url = f"{base_url}/new/?type=blank"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        project_name = f"test-blank-{int(time.time())}"

        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test blank project",
                "init_type": "gitea",
                "project_type": "local",
                "init_scitex": "true",
            },
            headers={"Referer": form_url},
            allow_redirects=False,
        )

        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_minimal(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from minimal template."""
        form_url = f"{base_url}/new/?type=template"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        project_name = f"test-minimal-{int(time.time())}"

        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test minimal template project",
                "init_type": "template",
                "template_type": "minimal",
                "project_type": "local",
                "init_scitex": "true",
            },
            headers={"Referer": form_url},
            allow_redirects=False,
        )

        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_research(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from research template."""
        form_url = f"{base_url}/new/?type=template"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        project_name = f"test-research-{int(time.time())}"

        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test research template project",
                "init_type": "template",
                "template_type": "research",
                "project_type": "local",
                "init_scitex": "true",
            },
            headers={"Referer": form_url},
            allow_redirects=False,
        )

        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_pip(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from pip_project template."""
        form_url = f"{base_url}/new/?type=template"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        project_name = f"test-pip-{int(time.time())}"

        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test pip project template",
                "init_type": "template",
                "template_type": "pip_project",
                "project_type": "local",
                "init_scitex": "true",
            },
            headers={"Referer": form_url},
            allow_redirects=False,
        )

        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    def test_project_name_validation_empty(self, authenticated_session, base_url):
        """Project creation should fail with empty name."""
        form_url = f"{base_url}/new/?type=blank"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": "",
                "description": "Test empty name validation",
                "init_type": "gitea",
                "project_type": "local",
            },
            headers={"Referer": form_url},
            allow_redirects=True,
        )

        # Should either stay on form (200) with error or redirect back
        assert resp.status_code == 200
        assert any(
            x in resp.text.lower() for x in ["error", "required", "invalid", "name"]
        )

    def test_project_name_validation_duplicate(
        self, authenticated_session, base_url, test_credentials
    ):
        """Project creation should fail with duplicate name."""
        form_url = f"{base_url}/new/?type=blank"
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        project_name = f"test-duplicate-{int(time.time())}"

        # Create first project
        resp1 = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "First project",
                "init_type": "gitea",
                "project_type": "local",
            },
            headers={"Referer": form_url},
            allow_redirects=False,
        )
        assert resp1.status_code in [200, 302]

        # Get new CSRF token for second request
        _, csrf_token = _get_csrf(authenticated_session, form_url)

        # Try to create duplicate
        resp2 = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "Duplicate project",
                "init_type": "gitea",
                "project_type": "local",
            },
            headers={"Referer": form_url},
            allow_redirects=True,
        )

        # Should fail with error
        assert resp2.status_code == 200
        assert any(
            x in resp2.text.lower() for x in ["exists", "duplicate", "already", "error"]
        )


class TestProjectAPI:
    """Test project-related APIs."""

    def test_file_tree_api_requires_valid_project(self, api_client, test_credentials):
        """File tree API returns error for invalid project."""
        username = test_credentials["username"]
        resp = api_client.get(f"/{username}/nonexistent-project-12345/api/file-tree/")
        assert resp.status_code in [404, 403, 302]

    def test_api_project_list(self, authenticated_session, base_url):
        """Project list API returns data."""
        resp = authenticated_session.get(f"{base_url}/project/api/list/")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))
