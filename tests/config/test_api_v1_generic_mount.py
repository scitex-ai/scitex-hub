#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/api/v1/<package>/ is mounted GENERICALLY: the hub knows no leaf API.

Leaves declare their operations through scitex-sdk (``scitex.apis``); the hub
adds one urlpatterns line (``scitex_sdk.app.api_serve.api_urlpatterns``) and
the SDK host hooks in settings. These tests pin that the mount happens, that
unknown v1 paths are problem+json rather than HTML, and that no hub source
outside tests names a leaf's API.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.test import Client
from django.urls import resolve

REPO = Path(__file__).resolve().parents[2]


def test_an_installed_leaf_api_is_mounted_by_discovery():
    # Arrange
    path = "/api/v1/dataset/datasets"
    # Act
    match = resolve(path)
    # Assert
    assert match.url_name == "api-dataset_datasets_list"


def test_an_unknown_v1_path_is_a_problem_not_an_html_page():
    # Arrange
    client = Client()
    # Act
    response = client.get("/api/v1/no-such-package/things")
    # Assert
    assert (response.status_code, response["Content-Type"]) == (
        404,
        "application/problem+json",
    )


def test_the_hubs_own_legacy_v1_routes_still_resolve():
    # Arrange
    path = "/api/v1/scholar/search/"
    # Act
    match = resolve(path)
    # Assert
    assert match.url_name != "api-not-found"


def test_no_hub_source_names_a_leaf_api():
    # Arrange: every .py under apps/ and config/ (tests excluded)
    pattern = re.compile(r"scitex_dataset\._rest|api/v1/dataset|dataset_datasets_")
    sources = [p for top in ("apps", "config") for p in (REPO / top).rglob("*.py")]
    # Act
    offenders = [
        str(p.relative_to(REPO))
        for p in sources
        if pattern.search(p.read_text(errors="ignore"))
    ]
    # Assert
    assert offenders == []
