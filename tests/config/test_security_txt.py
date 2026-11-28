"""/.well-known/security.txt (RFC 9116), /sitemap.xml and the CSP report sink.

The Expires guard is deliberate: an expired security.txt tells researchers
the contact is stale. This test goes red 30 days before
SECURITY_TXT_EXPIRES, so the renewal (bump the date, <= 1 year ahead) is a
failing CI leg rather than a silent lapse.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import pytest
from django.conf import settings
from django.test import RequestFactory

from config import security_views

rf = RequestFactory()


def test_security_txt_expires_is_more_than_30_days_away():
    # Arrange
    now = dt.datetime.now(dt.timezone.utc)
    # Act
    remaining = settings.SECURITY_TXT_EXPIRES - now
    # Assert
    assert remaining > dt.timedelta(days=30), (
        "security.txt expires soon: bump SECURITY_TXT_EXPIRES in "
        "config/settings/settings_security_headers.py (at most 1 year ahead)"
    )


def test_security_txt_expires_is_at_most_a_year_ahead():
    # Arrange
    now = dt.datetime.now(dt.timezone.utc)
    # Act
    ahead = settings.SECURITY_TXT_EXPIRES - now
    # Assert
    assert ahead <= dt.timedelta(days=366)


def test_security_txt_has_the_required_fields():
    # Arrange
    request = rf.get("/.well-known/security.txt")
    # Act
    response = security_views.security_txt(request)
    body = response.content.decode()
    # Assert
    assert (
        response["Content-Type"].startswith("text/plain"),
        "Contact: mailto:security@scitex.ai" in body,
        "Expires: " + settings.SECURITY_TXT_EXPIRES.strftime("%Y-%m-%dT%H:%M:%SZ")
        in body,
        "Preferred-Languages: en, ja" in body,
        "Canonical: https://scitex.ai/.well-known/security.txt" in body,
    ) == (True, True, True, True, True)


def test_security_txt_is_routed(client):
    # Arrange: nothing beyond the fixtures/settings
    # Act
    response = client.get("/.well-known/security.txt")
    # Assert
    assert response.status_code == 200


def test_sitemap_lists_public_pages_over_https(client):
    # Arrange: nothing beyond the fixtures/settings
    # Act
    response = client.get("/sitemap.xml", HTTP_HOST="testserver")
    body = response.content.decode()
    # Assert
    assert (
        response.status_code,
        "<loc>https://testserver/pricing/</loc>" in body,
        "/admin/" in body,
    ) == (200, True, False)


def test_every_sitemap_name_resolves():
    # Arrange
    from django.urls import reverse

    # Act
    urls = [reverse(name) for name in settings.SITEMAP_URL_NAMES]
    # Assert
    assert len(urls) == len(settings.SITEMAP_URL_NAMES)


def test_robots_txt_points_at_the_served_sitemap(client):
    # Arrange: nothing beyond the fixtures/settings
    # Act
    body = client.get("/robots.txt", HTTP_HOST="testserver").content.decode()
    # Assert
    assert "Sitemap: https://testserver/sitemap.xml" in body


@pytest.mark.parametrize(
    "payload",
    [
        {"csp-report": {"violated-directive": "script-src", "blocked-uri": "x"}},
        [{"type": "csp-violation", "body": {"effectiveDirective": "img-src"}}],
    ],
)
def test_csp_report_accepts_both_wire_formats_and_logs(payload, caplog):
    # Arrange
    request = rf.post(
        "/api/csp-report/",
        data=json.dumps(payload),
        content_type="application/csp-report",
    )
    # Act
    with caplog.at_level(logging.WARNING, logger="scitex_hub.security.csp"):
        response = security_views.csp_report(request)
    # Assert
    assert (response.status_code, "csp-violation" in caplog.text) == (204, True)


def test_csp_report_rejects_garbage_and_get():
    # Arrange: nothing beyond the fixtures/settings
    # Act
    bad = security_views.csp_report(
        rf.post("/api/csp-report/", data="{", content_type="application/json")
    )
    get = security_views.csp_report(rf.get("/api/csp-report/"))
    # Assert
    assert (bad.status_code, get.status_code) == (400, 405)


@pytest.mark.django_db
def test_csp_report_needs_no_csrf_token():
    # Arrange
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    # Act
    response = client.post(
        "/api/csp-report/",
        data=json.dumps({"csp-report": {"violated-directive": "img-src"}}),
        content_type="application/csp-report",
    )
    # Assert
    assert response.status_code == 204
