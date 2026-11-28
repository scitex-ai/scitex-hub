#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Hub's API surface is SDK-generated or a frozen, shrinking legacy list.

API contract v1 (scitex-sdk docs/design/api-contract-v1/01-rules.md):

- API-D001/D004: every Hub-implemented API-shaped route is either an SDK
  operation (mounted by ``api_urlpatterns``) or listed in
  ``config/api_legacy_allowlist.tsv``. A NEW hand-written route fails here.
- The allowlist only shrinks: an entry whose route is gone must be deleted.
- API-D003 / runtime admission: every trusted ``scitex.apis`` plugin is
  admitted (nothing refused), and every admitted plugin passes the SDK
  contract test.
- API-H003: public legacy routes carry Deprecation / Link headers.

All checks read the real URLconf and real routes; nothing is mocked.
"""

from __future__ import annotations

from django.test import Client, override_settings

from config.api_surface import (
    ALLOWLIST,
    LEGACY_DEPRECATIONS,
    api_routes,
    read_allowlist,
)


def test_every_hub_api_route_is_an_sdk_operation_or_allowlisted():
    # Arrange
    allowed = read_allowlist()
    # Act
    unlisted = sorted(set(api_routes()) - set(allowed))
    # Assert
    assert unlisted == [], (
        "hand-written API routes outside the legacy allowlist (API-D004); "
        "declare them as scitex-sdk operations instead: " + ", ".join(unlisted)
    )


def test_the_allowlist_only_shrinks():
    # Arrange
    present = set(api_routes())
    # Act
    stale = sorted(set(read_allowlist()) - present)
    # Assert
    assert stale == [], f"remove stale entries from {ALLOWLIST.name}: {stale}"


def test_every_trusted_plugin_is_admitted():
    # Arrange
    from scitex_sdk.app.api_serve import REFUSED

    import config.urls  # noqa: F401  (mounting runs admission)

    # Act
    refused = dict(REFUSED)
    # Assert
    assert refused == {}


def test_every_admitted_plugin_passes_the_sdk_contract():
    # Arrange
    from scitex_sdk.app.api_serve import admitted_plugins
    from scitex_sdk.testing.api_contract import declaration_violations

    # Act
    found = [
        str(v)
        for _ref, plugin in admitted_plugins()
        for v in declaration_violations(plugin)
    ]
    # Assert
    assert found == []


def test_a_public_legacy_route_carries_deprecation_headers():
    # Arrange
    client = Client()
    # Act
    response = client.get("/api/project/list/")
    # Assert
    assert (
        response.has_header("Deprecation"),
        "/api/v1/hub/projects" in response["Link"],
    ) == (
        True,
        True,
    )


def test_scholar_search_keeps_its_alias_twelve_months_after_beta():
    # Arrange
    from scitex_sdk.app.api_deprecation import headers_for, load

    deprecations, beta = load(LEGACY_DEPRECATIONS, "2027-01-31")
    # Act
    headers = headers_for("/api/v1/scholar/search/", deprecations, beta)
    # Assert
    assert headers["Sunset"] == "Mon, 31 Jan 2028 00:00:00 GMT"


def test_a_project_route_sunsets_six_months_after_beta():
    # Arrange
    with override_settings(SCITEX_API_BETA_LAUNCH_DATE="2027-01-31"):
        client = Client()
        # Act
        response = client.get("/api/project/list/")
    # Assert
    assert response["Sunset"] == "Sat, 31 Jul 2027 00:00:00 GMT"


def test_a_v1_operation_is_not_marked_deprecated():
    # Arrange
    client = Client()
    # Act
    response = client.get("/api/v1/dataset/datasets")
    # Assert
    assert response.has_header("Deprecation") is False
