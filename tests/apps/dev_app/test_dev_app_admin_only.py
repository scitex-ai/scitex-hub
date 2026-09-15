#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/dev/ pages are admin-only on prod, and the footer only advertises them to staff.

Site audit 2026-09-14 (hub-site-audit-2-defect-backlog-20260914): /dev/,
/dev/design/ and /dev/tests/web-api/ returned 200 to signed-out visitors and
the global footer linked two of them for everyone.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import override_settings
from django.urls import reverse

from apps.workspace.dev_app.access import dev_admin_only

WEB_API_TESTS_LINK = 'href="/dev/tests/web-api/"'


@pytest.fixture
def staff_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="dev-app-staff",
        password="test-password-123",
        is_staff=True,
    )
    client.force_login(user)
    return client


@pytest.fixture
def regular_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="dev-app-regular",
        password="test-password-123",
    )
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestDevAppGate:
    @override_settings(DEBUG=False)
    def test_anonymous_design_page_is_404_on_prod(self, client):
        # Arrange
        url = reverse("dev_app:design")
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 404

    @override_settings(DEBUG=False)
    def test_anonymous_web_api_tests_page_is_404_on_prod(self, client):
        # Arrange
        url = reverse("dev_app:tests_category", kwargs={"category": "web-api"})
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 404

    @override_settings(DEBUG=False)
    def test_regular_user_design_page_is_404_on_prod(self, regular_client):
        # Arrange
        url = reverse("dev_app:design")
        # Act
        response = regular_client.get(url)
        # Assert
        assert response.status_code == 404

    @override_settings(DEBUG=False)
    def test_staff_design_page_is_200_on_prod(self, staff_client):
        # Arrange
        url = reverse("dev_app:design")
        # Act
        response = staff_client.get(url)
        # Assert
        assert response.status_code == 200

    @override_settings(DEBUG=True)
    def test_anonymous_passes_gate_in_debug(self, rf):
        # Arrange
        # (Full-page render under DEBUG=True needs the Vite dev server, which the
        # test run lacks, so the gate is exercised on a trivial view instead.)
        request = rf.get("/dev/design/")
        request.user = AnonymousUser()
        view = dev_admin_only(lambda req: HttpResponse("open"))
        # Act
        response = view(request)
        # Assert
        assert response.status_code == 200


@pytest.mark.django_db
class TestFooterDevLinks:
    def test_anonymous_footer_lacks_web_api_tests_link(self, client):
        # Arrange
        url = reverse("public_app:about")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert WEB_API_TESTS_LINK not in content

    def test_staff_footer_has_web_api_tests_link(self, staff_client):
        # Arrange
        url = reverse("public_app:about")
        # Act
        content = staff_client.get(url).content.decode("utf-8")
        # Assert
        assert WEB_API_TESTS_LINK in content

    def test_anonymous_footer_keeps_web_api_docs_link(self, client):
        # Arrange
        url = reverse("public_app:about")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert f'href="{reverse("public_app:api_docs")}"' in content
