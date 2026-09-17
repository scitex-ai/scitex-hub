#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The visibility toggle at the request level: staff only, POST only, refusals honoured.

None of these render a page, so they run wherever Django is importable - the toggle's
contract is testable without the full application set.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest
from django.test import RequestFactory, override_settings

from apps.infra.public_app import clip_registry, demo_share

importlib.import_module("apps.infra.public_app.views.internal_demos")
internal_demos_module = sys.modules["apps.infra.public_app.views.internal_demos"]


class Person:
    def __init__(self, staff=False, authenticated=True, username="staffer"):
        self.is_staff = staff
        self.is_superuser = False
        self.is_authenticated = authenticated
        self.username = username


@pytest.fixture
def rf():
    return RequestFactory()


def seed(tmp_path, *, status="approved"):
    catalog = tmp_path / "demos-catalog.json"
    manifest = tmp_path / "projects-2026-09-17.manifest.json"
    manifest.write_text(json.dumps({
        "schema": "scitex.demo-video.manifest/1", "app": "projects", "date": "2026-09-17",
        "generated_at": "2026-09-17T10:00:00Z", "titles": {"en": "x"},
        "source": {"commit": "a" * 40, "branch": "develop", "dirty": False},
        "environment": {"voice": True},
        "renditions": [{"language": "en", "viewport": "desktop", "canonical": True,
                        "duration_seconds": 50.0,
                        "files": [{"role": "video", "name": "projects.en.mp4"}]}],
    }), encoding="utf-8")
    clip = clip_registry.register(catalog, manifest)
    if status == "approved":
        clip_registry.approve(catalog, clip["id"], by="operator", watched_seconds=50.0)
    elif status == "rejected":
        clip_registry.reject(catalog, clip["id"], by="operator", reason="dark")
    return catalog, clip["id"]


def toggle(rf, catalog, entry_id, visibility, *, person=None, method="post", passcode=""):
    store = catalog.with_name("demos-visibility.json")
    request = getattr(rf, method)(f"/internal/demos/visibility/",
                                 {"clip_id": entry_id, "visibility": visibility,
                                  "passcode": passcode})
    if person is not None:
        request.user = person
    request.session = {}
    with override_settings(DEMO_VIDEO_CATALOG=str(catalog),
                           DEMO_VIDEO_VISIBILITY_STORE=str(store)):
        response = internal_demos_module.visibility_view(request)
    return response, store, request


def test_a_get_cannot_change_visibility(tmp_path, rf):
    catalog, entry_id = seed(tmp_path)
    response, _, _ = toggle(rf, catalog, entry_id, "anyone-with-link", method="get")
    assert response.status_code == 405


def test_anonymous_and_non_staff_cannot_change_visibility(tmp_path, rf):
    catalog, entry_id = seed(tmp_path)
    anon, _, _ = toggle(rf, catalog, entry_id, "anyone-with-link")
    assert anon.status_code == 302
    assert "no-store" in anon["Cache-Control"]
    visitor, _, _ = toggle(rf, catalog, entry_id, "anyone-with-link", person=Person())
    assert visitor.status_code == 403


def test_staff_can_flip_an_approved_entry_outward_and_the_token_is_handed_over_once(
    tmp_path, rf
):
    catalog, entry_id = seed(tmp_path)
    response, store, request = toggle(rf, catalog, entry_id, "anyone-with-link",
                                      person=Person(staff=True))
    assert response.status_code == 302
    assert response["Location"].endswith(f"#entry-{entry_id}")
    minted = request.session["demo_share_minted_once"]
    assert minted["clip_id"] == entry_id
    assert demo_share.is_publicly_shared(demo_share.load_store(store), entry_id) is True
    # and the token is not in the redirect: it would land in history and logs
    assert minted["token"] not in response["Location"]


def test_a_draft_cannot_be_turned_outward_and_the_page_says_why(tmp_path, rf):
    catalog, entry_id = seed(tmp_path, status="draft")
    response, store, _ = toggle(rf, catalog, entry_id, "anyone-with-link",
                                person=Person(staff=True))
    assert response.status_code == 400
    assert "approved" in response["X-Demo-Refusal"]
    assert not store.exists()


def test_flipping_back_to_internal_revokes_the_link(tmp_path, rf):
    catalog, entry_id = seed(tmp_path)
    _, store, _ = toggle(rf, catalog, entry_id, "anyone-with-link", person=Person(staff=True))
    assert demo_share.is_publicly_shared(demo_share.load_store(store), entry_id) is True
    response, store, _ = toggle(rf, catalog, entry_id, "internal", person=Person(staff=True))
    assert response.status_code == 302
    assert demo_share.is_publicly_shared(demo_share.load_store(store), entry_id) is False


def test_a_passcode_can_be_set_when_going_outward(tmp_path, rf):
    catalog, entry_id = seed(tmp_path)
    _, store, _ = toggle(rf, catalog, entry_id, "anyone-with-link",
                         person=Person(staff=True), passcode="open-sesame")
    entry = demo_share.load_store(store)["entries"][0]
    assert entry["passcode_hash"].startswith("pbkdf2_")
    assert "open-sesame" not in store.read_text(encoding="utf-8")
