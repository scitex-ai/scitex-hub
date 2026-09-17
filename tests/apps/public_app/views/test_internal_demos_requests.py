#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The staff library at the request level: identity, cache, ranges, replaced bytes.

The review's seventh finding was that the rules were tested as functions while the
*responses* were not: who is refused, what a denial may be cached as, what a range
answer carries, and whether a hand-replaced video still reads as approved. These go
through the real views with the real settings override, so a regression in the wiring
fails here rather than in production.
"""

import json
from pathlib import Path

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

# The views package re-exports the view functions by name, so the module is imported
# by path: `from ...views import internal_demos` would bind the function.
from apps.infra.public_app import demo_library
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
def request_factory():
    return RequestFactory()


def write_render(directory: Path, *, language="en", video=b"a real video"):
    """A render on disk, with the digest the manifest records for its video."""
    directory.mkdir(parents=True, exist_ok=True)
    name = f"projects-2026-09-17.{language}.mp4"
    (directory / name).write_bytes(video)
    (directory / f"projects-2026-09-17.{language}.vtt").write_bytes(b"WEBVTT\n")
    digest = demo_library.sha256_file(directory / name)
    manifest = {
        "schema": demo_library.MANIFEST_SCHEMA,
        "app": "projects",
        "date": "2026-09-17",
        "generated_at": "2026-09-17T10:00:00Z",
        "source": {"commit": "b" * 40, "branch": "develop", "dirty": False},
        "renditions": [
            {
                "language": language,
                "viewport": "desktop",
                "canonical": True,
                "files": [
                    {"role": "video", "name": name, "sha256": digest, "size": len(video)},
                    {"role": "captions", "name": f"projects-2026-09-17.{language}.vtt",
                     "sha256": demo_library.sha256_file(
                         directory / f"projects-2026-09-17.{language}.vtt"),
                     "size": 7},
                ],
            }
        ],
    }
    (directory / "projects-2026-09-17.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return directory, name, manifest, digest


def test_an_anonymous_caller_is_sent_to_sign_in_and_nothing_is_cached(tmp_path, request_factory):
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(tmp_path)):
        response = internal_demos_module.internal_demos(request_factory.get("/internal/demos/"))
    assert response.status_code == 302
    assert "/auth/signin/" in response["Location"]
    assert response["Cache-Control"] == "private, no-store"
    assert "noindex" in response["X-Robots-Tag"]


def test_a_signed_in_non_staff_caller_is_refused_and_nothing_is_cached(tmp_path, request_factory):
    request = request_factory.get("/internal/demos/")
    request.user = Person()
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(tmp_path)):
        response = internal_demos_module.internal_demos(request)
    assert response.status_code == 403
    assert response["Cache-Control"] == "private, no-store"


def test_staff_see_the_card_and_a_malformed_manifest_next_to_it_does_not_500(
    tmp_path, request_factory
):
    directory, _, _, _ = write_render(tmp_path)
    # The review's malformed case: the right schema and the wrong shapes.
    (directory / "broken.manifest.json").write_text(
        json.dumps({"schema": demo_library.MANIFEST_SCHEMA, "app": "projects",
                    "date": "2026-09-17", "renditions": "not a list"}),
        encoding="utf-8",
    )
    request = request_factory.get("/internal/demos/")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        response = internal_demos_module.internal_demos(request)
    assert response.status_code == 200
    assert b"projects-2026-09-17.manifest.json" in response.content
    assert response["Cache-Control"] == "private, no-store"


def test_a_hand_replaced_video_still_serves_and_the_mismatch_is_reported(
    tmp_path, request_factory
):
    # MVP: a recorded SHA is optional and informational, so a replaced file does not
    # take the asset off the air — the catalog says the bytes changed, and that is all.
    directory, name, _, _ = write_render(tmp_path)
    (directory / name).write_bytes(b"somebody replaced this by hand")
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        index = demo_library.library_index(directory)
    entry = index["entries"][0]
    assert entry["files_present"] is True
    assert entry["status"] == "ready"
    assert entry["sha_optional_mismatch"] == ["en"]


def test_a_missing_video_makes_the_entry_incomplete(tmp_path, request_factory):
    # The one existence rule the MVP does enforce: the files it names must be there.
    directory, name, _, _ = write_render(tmp_path)
    (directory / name).unlink()
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        index = demo_library.library_index(directory)
    entry = index["entries"][0]
    assert entry["files_present"] is False
    assert entry["status"] == "incomplete"
    assert entry["missing_files"] == ["en"]


def test_a_render_with_no_recorded_sha_is_ready_when_the_files_are_there(
    tmp_path, request_factory
):
    # A single optional SHA per file: absent means "not supplied", not "broken".
    directory, name, _, _ = write_render(tmp_path)
    manifest_path = directory / "projects-2026-09-17.manifest.json"
    import json as _json
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["renditions"][0]["files"]:
        record.pop("sha256", None)
    manifest_path.write_text(_json.dumps(manifest), encoding="utf-8")
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        index = demo_library.library_index(directory)
    entry = index["entries"][0]
    assert entry["files_present"] is True
    assert entry["status"] == "ready"
    assert entry["sha_optional_mismatch"] == []


def test_a_whole_file_request_advertises_ranges(tmp_path, request_factory):
    directory, name, _, _ = write_render(tmp_path)
    request = request_factory.get(f"/internal/demos/media/{name}")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        response = internal_demos_module.internal_demo_media(request, name)
    assert response.status_code == 200
    assert response["Accept-Ranges"] == "bytes"
    assert response["Cache-Control"] == "private, no-store"


def test_a_bounded_range_returns_206_with_content_range_and_only_that_slice(
    tmp_path, request_factory
):
    video = b"0123456789" * 100
    directory, name, _, _ = write_render(tmp_path, video=video)
    request = request_factory.get(f"/internal/demos/media/{name}", HTTP_RANGE="bytes=10-19")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        response = internal_demos_module.internal_demo_media(request, name)
    body = b"".join(response.streaming_content)
    assert response.status_code == 206
    assert response["Content-Range"] == f"bytes 10-19/{len(video)}"
    assert response["Content-Length"] == "10"
    assert body == video[10:20]


def test_an_unsatisfiable_range_returns_416_with_the_real_size(tmp_path, request_factory):
    directory, name, _, _ = write_render(tmp_path)
    request = request_factory.get(f"/internal/demos/media/{name}",
                                  HTTP_RANGE="bytes=99999999-")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        response = internal_demos_module.internal_demo_media(request, name)
    assert response.status_code == 416
    assert response["Content-Range"].startswith("bytes */")
    assert response["Accept-Ranges"] == "bytes"


def test_media_for_an_anonymous_caller_is_refused_and_not_cached(tmp_path, request_factory):
    directory, name, _, _ = write_render(tmp_path)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        response = internal_demos_module.internal_demo_media(
            request_factory.get(f"/internal/demos/media/{name}"), name
        )
    assert response.status_code == 302
    assert response["Cache-Control"] == "private, no-store"


def test_a_name_that_leaves_the_library_is_a_404(tmp_path, request_factory):
    directory, name, _, _ = write_render(tmp_path)
    outside = tmp_path.parent / "outside.mp4"
    outside.write_bytes(b"not yours")
    request = request_factory.get("/internal/demos/media/anything")
    request.user = Person(staff=True)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        for hostile in ("../outside.mp4", f"../{outside.name}", "/etc/passwd", ".hidden"):
            with pytest.raises(Http404):
                internal_demos_module.internal_demo_media(request, hostile)


def test_a_symlinked_media_file_cannot_leave_the_library(tmp_path, request_factory):
    directory, _, _, _ = write_render(tmp_path)
    outside = tmp_path.parent / "secret.mp4"
    outside.write_bytes(b"secret bytes")
    (directory / "link.mp4").symlink_to(outside)
    with override_settings(DEMO_VIDEO_LIBRARY_DIR=str(directory)):
        assert demo_library.resolve_media(directory, "link.mp4") is None
