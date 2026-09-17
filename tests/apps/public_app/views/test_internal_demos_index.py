#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The progress index at the request level: who sees it, what it shows, what it never does.

The page exists because renders posted to chat vanish from the feed, so these tests are
about the promise that makes it useful: latest first, statuses exactly as the catalog says,
rejected history still visible, defects listed, play and download working, and no path by
which a request can change a status.
"""

import json
from pathlib import Path

import pytest
from django.test import RequestFactory, override_settings

from apps.infra.public_app import clip_registry, demo_library
from apps.infra.public_app.views import internal_demos as _views_package  # noqa: F401
import apps.infra.public_app.views.internal_demos as internal_demos_module

pytestmark = pytest.mark.django_db


class Person:
    """The smallest user the access check needs; the real one is a Django user."""

    def __init__(self, *, authenticated=True, staff=False, superuser=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = superuser
        self.username = "staffer" if (staff or superuser) else "visitor"


@pytest.fixture
def rf():
    return RequestFactory()


def make_render(directory: Path, *, app="projects", date="2026-09-17", language="en",
                seconds=50.0, defects_ok=True):
    """A manifest, its real media, and the media names the index will link to."""
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{app}-{date}"
    video = f"{stem}.{language}.mp4"
    captions = f"{stem}.{language}.vtt"
    for name, payload in ((video, b"video bytes"), (captions, b"WEBVTT\n")):
        (directory / name).write_bytes(payload)
    manifest = {
        "schema": demo_library.MANIFEST_SCHEMA,
        "app": app,
        "date": date,
        "generated_at": f"{date}T10:00:00Z",
        "titles": {language: "Create your first project"},
        "source": {"commit": "a" * 40, "branch": "develop", "dirty": False},
        "environment": {"voice": True, "narration_failures": {}},
        "renditions": [{
            "language": language, "ui_locale": language, "viewport": "desktop",
            "canonical": True, "duration_seconds": seconds,
            "files": [
                {"role": "video", "name": video,
                 "sha256": demo_library.sha256_file(directory / video)},
                {"role": "captions", "name": captions,
                 "sha256": demo_library.sha256_file(directory / captions)},
            ],
        }],
    }
    path = directory / f"{stem}.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def seed(tmp_path: Path, *, rejected=False):
    """A library directory and a catalog with one Draft (and optionally one Rejected)."""
    media = tmp_path / "media"
    catalog = tmp_path / "demos-catalog.json"
    first = clip_registry.register(catalog, make_render(media, date="2026-09-17"))
    clip_registry.approve(catalog, first["id"], by="operator", watched_seconds=50.0)
    second = clip_registry.register(catalog, make_render(media, date="2026-09-16"))
    if rejected:
        clip_registry.reject(catalog, second["id"], by="operator",
                             reason="interface was dark from the workspace onward")
    return media, catalog, first, second


def index(request_factory, media, catalog, *, person=None, query=""):
    request = request_factory.get(f"/internal/demos/{query}")
    if person is not None:
        request.user = person
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(media),
                           DEMO_VIDEO_CATALOG=str(catalog)):
        return internal_demos_module.internal_demos(request)


def test_an_anonymous_caller_is_sent_to_sign_in_and_nothing_is_cached(tmp_path, rf):
    media, catalog, _, _ = seed(tmp_path)
    response = index(rf, media, catalog)
    assert response.status_code == 302
    assert "/auth/signin/" in response["Location"]
    assert response["Cache-Control"] == "private, no-store"
    assert "noindex" in response["X-Robots-Tag"]


def test_a_signed_in_non_staff_caller_is_refused_and_nothing_is_cached(tmp_path, rf):
    media, catalog, _, _ = seed(tmp_path)
    response = index(rf, media, catalog, person=Person())
    assert response.status_code == 403
    assert response["Cache-Control"] == "private, no-store"


def test_staff_see_every_entry_latest_first_with_its_provenance(tmp_path, rf):
    media, catalog, first, second = seed(tmp_path)
    response = index(rf, media, catalog, person=Person(staff=True))
    body = response.content.decode()
    assert response.status_code == 200
    # latest first: the 09-17 entry precedes the 09-16 one
    assert body.index("2026-09-17") < body.index("2026-09-16")
    for identifier in (first["id"], second["id"]):
        assert identifier in body
    assert "a" * 12 in body                      # the development commit is shown
    assert "Approved" in body and "Draft" in body
    assert "projects" in body                    # the flow
    assert "Play" in body and "Download" in body


def test_the_only_filters_are_flow_and_status(tmp_path, rf):
    media, catalog, first, second = seed(tmp_path, rejected=True)
    only_drafts = index(rf, media, catalog, person=Person(staff=True), query="?status=draft")
    assert first["id"] not in only_drafts.content.decode()
    assert second["id"] in only_drafts.content.decode()
    only_rejected = index(rf, media, catalog, person=Person(staff=True), query="?status=rejected")
    assert "Rejected" in only_rejected.content.decode()
    other_flow = index(rf, media, catalog, person=Person(staff=True), query="?flow=scholar")
    assert first["id"] not in other_flow.content.decode()


def test_a_rejected_take_stays_visible_with_its_reason(tmp_path, rf):
    media, catalog, _, second = seed(tmp_path, rejected=True)
    body = index(rf, media, catalog, person=Person(staff=True)).content.decode()
    assert second["id"] in body
    assert "interface was dark from the workspace onward" in body
    assert clip_registry.load_catalog(catalog)["clips"][1]["status"] == "rejected"


def test_a_malformed_catalog_does_not_500_the_page(tmp_path, rf):
    media, catalog, first, _ = seed(tmp_path)
    catalog.write_text("{ this is not json", encoding="utf-8")
    response = index(rf, media, catalog, person=Person(staff=True))
    assert response.status_code == 200
    assert first["id"] not in response.content.decode()


def test_play_streams_and_download_is_an_attachment(tmp_path, rf):
    media, catalog, _, _ = seed(tmp_path)
    name = "projects-2026-09-17.en.mp4"
    request = rf.get(f"/internal/demos/media/{name}")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(media), DEMO_VIDEO_CATALOG=str(catalog)):
        play = internal_demos_module.internal_demo_media(request, name)
        ranged = internal_demos_module.internal_demo_media(
            rf.get(f"/internal/demos/media/{name}", HTTP_RANGE="bytes=0-4"), name
        )
        downloaded = internal_demos_module.internal_demo_media(
            rf.get(f"/internal/demos/media/{name}", {"download": "1"}), name
        )
    assert play.status_code == 200
    assert "Content-Disposition" not in play          # play streams in place
    assert play["Accept-Ranges"] == "bytes"
    assert play["Cache-Control"] == "private, no-store"
    assert ranged.status_code == 206
    assert ranged["Content-Range"].startswith("bytes 0-4/")
    assert b"".join(ranged.streaming_content) == b"video"   # exactly the requested slice
    assert downloaded["Content-Disposition"].startswith("attachment;")
    assert downloaded["Cache-Control"] == "private, no-store"


def test_a_traversal_name_is_a_404(tmp_path, rf):
    from django.http import Http404

    media, catalog, _, _ = seed(tmp_path)
    request = rf.get("/internal/demos/media/x")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(media), DEMO_VIDEO_CATALOG=str(catalog)):
        for hostile in ("../projects-2026-09-17.en.mp4", "/etc/passwd", ".hidden"):
            with pytest.raises(Http404):
                internal_demos_module.internal_demo_media(request, hostile)


def test_nothing_in_the_view_can_change_a_status(tmp_path, rf):
    # Arrange: the catalog is the only source of status, and the view only reads it.
    media, catalog, first, _ = seed(tmp_path)
    before = json.dumps(clip_registry.load_catalog(catalog), sort_keys=True)
    # Act: every request the page offers, including the download and a filter query.
    for query in ("", "?status=draft", "?flow=projects", "?status=approved"):
        index(rf, media, catalog, person=Person(staff=True), query=query)
    # Assert
    assert json.dumps(clip_registry.load_catalog(catalog), sort_keys=True) == before
