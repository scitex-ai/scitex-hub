#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The status banner says "outage" only when a service is actually down.

Dev walkthrough 2026-09-14: 7 of 9 services up and 2 merely degraded rendered
"Partial System Outage". Degraded-only now reads "Degraded performance", the
page is translated into Japanese, and "last checked" is a readable time rather
than a raw ISO string. Real test client, seeded cache, no mocks.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.cache import cache
from django.utils import translation

from apps.infra.public_app.views.status.public_status import (
    PUBLIC_STATUS_CACHE_KEY,
    _compute_overall,
    with_checked_at_datetime,
)

PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _services(*statuses):
    return [
        {
            "name": f"svc-{i}",
            "status": status,
            "uptime_days": ["operational"] * 89 + [status],
            "uptime_pct": "98.89",
        }
        for i, status in enumerate(statuses)
    ]


SEVEN_UP_TWO_DEGRADED = _services(*(["operational"] * 7 + ["degraded"] * 2))


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the JA assertions read a real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()
    yield


@pytest.fixture
def seeded_degraded_status():
    cache.set(
        PUBLIC_STATUS_CACHE_KEY,
        {
            "overall": _compute_overall(SEVEN_UP_TWO_DEGRADED),
            "services": SEVEN_UP_TWO_DEGRADED,
            "checked_at": "2026-09-14T18:05:00+00:00",
        },
        300,
    )
    yield
    cache.delete(PUBLIC_STATUS_CACHE_KEY)


def _status_page(client, language="en"):
    cookie = {"HTTP_COOKIE": "django_language=ja"} if language == "ja" else {}
    return client.get("/status/", **cookie).content.decode("utf-8")


def _banner_text(html):
    # The banner also carries every state's label in data-* attributes for the JS refresh.
    match = re.search(r'id="overall-banner"[^>]*>(.*?)</div>', html, flags=re.S)
    return match.group(1).strip() if match else ""


def test_degraded_services_without_a_down_one_are_degraded():
    # Arrange
    services = SEVEN_UP_TWO_DEGRADED

    # Act
    overall = _compute_overall(services)

    # Assert
    assert overall == "degraded"


def test_one_down_service_is_a_partial_outage():
    # Arrange
    services = _services("operational", "degraded", "down")

    # Act
    overall = _compute_overall(services)

    # Assert
    assert overall == "partial_outage"


def test_every_service_down_is_a_major_outage():
    # Arrange
    services = _services("down", "down")

    # Act
    overall = _compute_overall(services)

    # Assert
    assert overall == "down"


def test_all_operational_is_operational():
    # Arrange
    services = _services("operational", "operational")

    # Act
    overall = _compute_overall(services)

    # Assert
    assert overall == "operational"


def test_unparseable_checked_at_leaves_no_datetime():
    # Arrange
    data = {"checked_at": "not-a-time"}

    # Act
    enriched = with_checked_at_datetime(data)

    # Assert
    assert enriched["checked_at_dt"] is None


@pytest.mark.django_db
def test_status_page_shows_degraded_performance(client, seeded_degraded_status):
    # Arrange
    expected = "Degraded performance"

    # Act
    html = _status_page(client)

    # Assert
    assert expected in html


@pytest.mark.django_db
def test_status_page_does_not_claim_an_outage_when_only_degraded(
    client, seeded_degraded_status
):
    # Arrange
    outage_copy = "System Outage"

    # Act
    banner = _banner_text(_status_page(client))

    # Assert
    assert outage_copy not in banner


@pytest.mark.django_db
def test_status_page_last_checked_is_human_readable(client, seeded_degraded_status):
    # Arrange
    readable = "Sept. 14, 2026, 6:05 p.m. UTC</time>"

    # Act
    html = _status_page(client)

    # Assert
    assert readable in html


@pytest.mark.django_db
def test_status_page_banner_is_japanese_for_japanese_visitors(
    client, seeded_degraded_status
):
    # Arrange
    expected = "一部のサービスでパフォーマンスが低下しています"

    # Act
    html = _status_page(client, language="ja")

    # Assert
    assert expected in html


@pytest.mark.django_db
def test_server_status_page_shows_degraded_performance_in_japanese(
    client, seeded_degraded_status
):
    # Arrange
    expected = "一部のサービスでパフォーマンスが低下しています"

    # Act
    html = client.get("/server-status/", HTTP_COOKIE="django_language=ja").content.decode(
        "utf-8"
    )

    # Assert
    assert expected in html
