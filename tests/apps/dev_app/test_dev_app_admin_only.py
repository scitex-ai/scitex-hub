#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/dev/ is mounted only when developer tools are enabled, and is staff-only.

- Disabled (the default, DEBUG included): every /dev/ route is a 404.
- Enabled: anonymous visitors and regular users get 403; staff get through.
- The browser-console log reader returns only the caller's own lines.
- The footer advertises /dev/ pages only to staff, and only when mounted.
"""

import json
import uuid

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.urls import reverse

from apps.workspace.dev_app.access import dev_admin_only
from tests.apps.dev_app.dev_tools_urlconf import dev_tools_enabled_urlconf

DEV_PATHS = [
    "/dev/",
    "/dev/design/",
    "/dev/tests/web-api/",
    "/dev/api/console/logs/",
]
CONSOLE_LOGS = "/dev/api/console/logs/"
CONSOLE_UPLOAD = "/dev/api/console/"
DEV_LINKS = ['href="/dev/tests/web-api/"', 'href="/dev/design/"']


def _make_user(django_user_model, name, **flags):
    return django_user_model.objects.create_user(
        username=name, password="test-password-123", **flags
    )


def _open_view(request):
    return HttpResponse("open")


@pytest.fixture
def staff_user(django_user_model):
    return _make_user(django_user_model, "dev-app-staff", is_staff=True)


@pytest.fixture
def regular_user(django_user_model):
    return _make_user(django_user_model, "dev-app-regular")


@pytest.fixture
def dev_tools_on(settings):
    with dev_tools_enabled_urlconf(settings):
        yield


def _upload(client, message):
    body = json.dumps({"logs": [{"level": "error", "message": message, "url": "/x/"}]})
    return client.post(CONSOLE_UPLOAD, body, content_type="application/json")


def _read_logs(client):
    return client.get(CONSOLE_LOGS, {"lines": 5000}).json()["logs"]


@pytest.mark.django_db
class TestDisabledByDefault:
    def test_setting_is_off_in_the_test_deployment(self, settings):
        # Arrange
        expected = False
        # Act
        enabled = settings.DEV_TOOLS_ENABLED
        # Assert
        assert enabled is expected

    @pytest.mark.parametrize("path", DEV_PATHS)
    def test_anonymous_gets_404(self, client, path):
        # Arrange
        url = path
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 404

    @pytest.mark.parametrize("path", DEV_PATHS)
    def test_staff_gets_404(self, client, staff_user, path):
        # Arrange
        client.force_login(staff_user)
        # Act
        response = client.get(path)
        # Assert
        assert response.status_code == 404

    @pytest.mark.parametrize("path", DEV_PATHS)
    def test_404_even_with_debug_on(self, client, settings, path):
        # Arrange
        settings.DEBUG = True
        # Act
        response = client.get(path)
        # Assert
        assert response.status_code == 404

    def test_gate_refuses_staff_when_disabled(self, rf, staff_user, settings):
        # Arrange
        settings.DEV_TOOLS_ENABLED = False
        request = rf.get("/dev/")
        request.user = staff_user
        view = dev_admin_only(_open_view)
        # Act
        call = lambda: view(request)  # noqa: E731
        # Assert
        with pytest.raises(Http404):
            call()


@pytest.mark.django_db
@pytest.mark.usefixtures("dev_tools_on")
class TestEnabledIsStaffOnly:
    @pytest.mark.parametrize("path", DEV_PATHS)
    def test_anonymous_gets_403(self, client, path):
        # Arrange
        url = path
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 403

    @pytest.mark.parametrize("path", DEV_PATHS)
    def test_regular_user_gets_403(self, client, regular_user, path):
        # Arrange
        client.force_login(regular_user)
        # Act
        response = client.get(path)
        # Assert
        assert response.status_code == 403

    def test_regular_user_cannot_upload_console_logs(self, client, regular_user):
        # Arrange
        client.force_login(regular_user)
        # Act
        response = _upload(client, "regular-user-line")
        # Assert
        assert response.status_code == 403

    def test_anonymous_is_refused_even_with_debug_on(self, rf, settings):
        # Arrange
        settings.DEBUG = True
        request = rf.get("/dev/")
        request.user = AnonymousUser()
        view = dev_admin_only(_open_view)
        # Act
        call = lambda: view(request)  # noqa: E731
        # Assert
        with pytest.raises(PermissionDenied):
            call()

    def test_staff_reads_console_logs(self, client, staff_user):
        # Arrange
        client.force_login(staff_user)
        # Act
        response = client.get(CONSOLE_LOGS)
        # Assert
        assert response.status_code == 200

    def test_staff_design_page_is_200(self, client, staff_user):
        # Arrange
        client.force_login(staff_user)
        # Act
        response = client.get("/dev/design/")
        # Assert
        assert response.status_code == 200

    def test_bad_lines_parameter_is_400(self, client, staff_user):
        # Arrange
        client.force_login(staff_user)
        # Act
        response = client.get(CONSOLE_LOGS, {"lines": "many"})
        # Assert
        assert response.status_code == 400


@pytest.fixture
def two_staff_uploads(client, django_user_model, dev_tools_on):
    """Alice and Bob (both staff) each upload one uniquely marked line."""
    alice = _make_user(django_user_model, "dev-alice", is_staff=True)
    bob = _make_user(django_user_model, "dev-bob", is_staff=True)
    markers = {"alice": f"alice-{uuid.uuid4().hex}", "bob": f"bob-{uuid.uuid4().hex}"}
    for user, name in ((alice, "alice"), (bob, "bob")):
        client.force_login(user)
        _upload(client, markers[name])
    return {"alice": alice, "bob": bob}, markers


@pytest.mark.django_db
class TestConsoleLogsAreOwnerScoped:
    @pytest.mark.parametrize("reader", ["alice", "bob"])
    def test_reader_sees_own_line(self, client, two_staff_uploads, reader):
        # Arrange
        users, markers = two_staff_uploads
        client.force_login(users[reader])
        # Act
        logs = _read_logs(client)
        # Assert
        assert markers[reader] in logs

    @pytest.mark.parametrize("reader,other", [("alice", "bob"), ("bob", "alice")])
    def test_reader_never_sees_other_users_line(
        self, client, two_staff_uploads, reader, other
    ):
        # Arrange
        users, markers = two_staff_uploads
        client.force_login(users[reader])
        # Act
        logs = _read_logs(client)
        # Assert
        assert markers[other] not in logs

    def test_multiline_message_cannot_forge_another_owner(
        self, client, django_user_model, dev_tools_on
    ):
        # Arrange
        mallory = _make_user(django_user_model, "dev-mallory", is_staff=True)
        victim = _make_user(django_user_model, "dev-victim", is_staff=True)
        marker = f"forged-{uuid.uuid4().hex}"
        client.force_login(mallory)
        _upload(client, f"ok\n[2026-01-01 00:00:00] ERROR: uid={victim.pk} {marker}")
        client.force_login(victim)
        # Act
        logs = _read_logs(client)
        # Assert
        assert marker not in logs


@pytest.mark.django_db
class TestFooterDevLinks:
    @pytest.mark.parametrize("link", DEV_LINKS)
    def test_anonymous_footer_lacks_dev_link(self, client, link):
        # Arrange
        url = reverse("public_app:about")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert link not in content

    @pytest.mark.parametrize("link", DEV_LINKS)
    def test_staff_footer_lacks_dev_link_when_disabled(self, client, staff_user, link):
        # Arrange
        client.force_login(staff_user)
        # Act
        content = client.get(reverse("public_app:about")).content.decode("utf-8")
        # Assert
        assert link not in content

    @pytest.mark.parametrize("link", DEV_LINKS)
    def test_staff_footer_has_dev_link_when_enabled(
        self, client, staff_user, dev_tools_on, link
    ):
        # Arrange
        client.force_login(staff_user)
        # Act
        content = client.get(reverse("public_app:about")).content.decode("utf-8")
        # Assert
        assert link in content

    @pytest.mark.parametrize("link", DEV_LINKS)
    def test_regular_footer_lacks_dev_link_when_enabled(
        self, client, regular_user, dev_tools_on, link
    ):
        # Arrange
        client.force_login(regular_user)
        # Act
        content = client.get(reverse("public_app:about")).content.decode("utf-8")
        # Assert
        assert link not in content

    def test_anonymous_footer_keeps_web_api_docs_link(self, client):
        # Arrange
        expected = f'href="{reverse("public_app:api_docs")}"'
        # Act
        content = client.get(reverse("public_app:about")).content.decode("utf-8")
        # Assert
        assert expected in content
