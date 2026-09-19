#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The staff library's route, gate and template contracts.

The behavioural checks (anonymous is redirected, a signed-in non-staff account gets
403, staff sees the cards, the media route refuses traversal) need the Django test
client and run in CI. These are the cheap half that must not drift while that runs:
the gate is called first in both views, the media response is not cacheable, the
template is reduced-motion safe and never points at a public /media/ path, and the
route is resolved before the <str:username>/ catch-all that would otherwise read
"internal" as somebody's username.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_APP = REPO_ROOT / "apps" / "infra" / "public_app"
VIEW = PUBLIC_APP / "views" / "internal_demos.py"
URLS = PUBLIC_APP / "urls" / "pages.py"
TEMPLATE = PUBLIC_APP / "templates" / "public_app" / "pages" / "internal_demos.html"
SETTINGS = REPO_ROOT / "config" / "settings" / "settings_static.py"
CONFIG_URLS = REPO_ROOT / "config" / "urls.py"


def view_source() -> str:
    return VIEW.read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    """The source of one top-level function, from its def to the next def."""
    start = source.index(f"def {name}(")
    rest = source[start:]
    end = rest.find("\ndef ", 1)
    return rest if end == -1 else rest[:end]


def test_both_views_gate_access_before_they_do_anything():
    # Arrange
    source = view_source()
    # Act
    library_body = function_body(source, "index_view")
    media_body = function_body(source, "media_view")
    # Assert: the gate is the first statement of each, not a later courtesy.
    assert "Latest first" in library_body.splitlines()[1]
    assert "denial = access_denied(request)" in library_body
    assert library_body.index("access_denied(request)") < library_body.index("load_catalog(")
    assert media_body.index("access_denied(request)") < media_body.index("resolve_media(")


def test_the_gate_reuses_the_existing_instance_admin_test():
    # Arrange / Act
    source = view_source()
    # Assert: no new authorization concept, and no shared page password.
    assert "from .status.access import is_instance_admin" in source
    assert "is_instance_admin(user)" in source
    lowered = source.lower()
    assert "password" not in lowered.replace("no shared page password", "")
    assert "secret" not in lowered


def test_the_views_are_plain_functions_not_decorated_wrappers():
    # Arrange / Act
    lines = view_source().splitlines()
    decorated = [
        lines[index - 1].strip()
        for index, line in enumerate(lines)
        if line.startswith(("def index_view", "def media_view"))
    ]
    # Assert: routing tests assert resolve(path).func is <view>.
    assert all(not line.startswith("@") for line in decorated)


def test_media_is_served_through_the_sanitizer_and_is_not_cacheable():
    # Arrange / Act
    body = function_body(view_source(), "media_view")
    # Assert
    assert "demo_library.resolve_media(directory, name)" in body
    assert 'response["Cache-Control"] = "private, no-store"' in body
    assert 'response["X-Robots-Tag"] = "noindex, nofollow"' in body
    assert "FileResponse" in body
    # A missing file and a refused name answer the same way, on purpose.
    assert "raise Http404" in body


def test_the_routes_are_registered_with_names_the_view_reverses():
    # Arrange
    urls = URLS.read_text(encoding="utf-8")
    # Act / Assert
    assert 'path("internal/demos/", views.internal_demos, name="internal_demos")' in urls
    assert 'path("internal/demos/media/<path:name>", views.internal_demo_media' in urls
    assert "public_app:internal_demo_media" in view_source()


def test_the_internal_route_is_resolved_before_the_username_catch_all():
    # Arrange: /internal/ must not be read as a username by the last route.
    config = CONFIG_URLS.read_text(encoding="utf-8")
    # Act
    public_app_include = config.index('include("apps.infra.public_app.urls")')
    username_catch_all = config.index('path("<str:username>/"')
    # Assert
    assert public_app_include < username_catch_all


def test_the_library_directory_is_not_under_the_public_media_root():
    # Arrange: MEDIA_ROOT is served to anyone who knows the path.
    settings = SETTINGS.read_text(encoding="utf-8")
    # Act
    entry = re.search(r'"DEMO_VIDEO_LIBRARY_DIR":\s*([^,\n]+),', settings)
    # Assert
    assert entry, "DEMO_VIDEO_LIBRARY_DIR must be declared"
    assert "MEDIA_ROOT" not in entry.group(1)
    assert "internal_demos" in entry.group(1)


def test_the_template_is_reduced_motion_safe_and_never_links_public_media():
    # Arrange: the comment explaining the no-animation choice must not count as one.
    template = TEMPLATE.read_text(encoding="utf-8")
    without_comments = re.sub(r"/\*.*?\*/", "", template, flags=re.DOTALL)
    without_comments = re.sub(r"{#.*?#}", "", without_comments, flags=re.DOTALL)
    # Act / Assert: no animation to reduce, and no /media/ URL to leak past the gate.
    assert "animation:" not in without_comments
    assert "transition:" not in without_comments
    assert "/media/" not in template
    assert "file.play_url" in template, "links come from the authorized media route"
    assert "file.download_url" in template


def test_the_template_stacks_to_one_column_on_a_phone():
    # Arrange / Act
    template = TEMPLATE.read_text(encoding="utf-8")
    # Assert
    assert "@media (max-width: 480px)" in template
    assert "grid-template-columns: 1fr" in template


def test_each_video_is_an_inline_thumbnail_player_not_just_a_link():
    template = TEMPLATE.read_text(encoding="utf-8")
    assert '<video controls playsinline preload="metadata"' in template
    assert 'poster="{{ file.poster_url }}"' in template
    assert '<source src="{{ file.play_url }}" type="video/mp4">' in template
    assert 'kind="captions"' in template
    assert "autoplay" not in template
    assert ".media-actions" in template
    assert "min-height: 44px" in template
    assert "flex-wrap: wrap" in template


def test_the_template_shows_the_facts_a_card_must_not_invent():
    # Arrange: the card list from hub-internal-demo-video-library-20260917.
    template = TEMPLATE.read_text(encoding="utf-8")
    # Act / Assert
    for field in (
        "card.flow",
        "card.date",
        "card.dev_commit_short",
        "card.viewports",
        "card.status",
        "card.languages",
        "card.files",
    ):
        assert field in template, field
    assert "card.defects" in template
