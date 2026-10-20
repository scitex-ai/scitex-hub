#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The catalog entry -> player renditions mapping, and the publishing metadata.

These are the rules the player's language switch depends on: which files a
language has, what a button is called, which rendition a visitor starts on, and
that captions follow the narration rather than the UI.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "apps" / "infra" / "public_app" / "views" / "demo_video_languages.py"


def load_module():
    """Load the mapping module directly: the views package __init__ imports the
    whole app, which these pure functions do not need."""
    spec = importlib.util.spec_from_file_location("demo_video_languages", MODULE_PATH)
    assert spec is not None and spec.loader is not None, MODULE_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_video_languages"] = module
    spec.loader.exec_module(module)
    return module


demo_video_languages = load_module()
default_captions = demo_video_languages.default_captions
default_language = demo_video_languages.default_language
languages_for = demo_video_languages.languages_for
rendition_code = demo_video_languages.rendition_code

# The shape the two published guides use in pages_data.VIDEO_CATALOG.
PUBLISHED_GUIDE = {
    "title": "Create your first project",
    "url": "/media/videos/demos/projects-2026-09-14.en.mp4",
    "ja_url": "/media/videos/demos/projects-2026-09-14.ja.mp4",
    "captions": "/media/videos/demos/projects-2026-09-14.en.vtt",
    "ja_captions": "/media/videos/demos/projects-2026-09-14.ja.vtt",
    "narrated": True,
}


def test_published_guide_becomes_two_renditions_with_captions():
    # Arrange / Act
    renditions = languages_for(PUBLISHED_GUIDE)
    # Assert
    assert [entry["code"] for entry in renditions] == ["en", "ja"]
    assert renditions[1] == {
        "code": "ja",
        "language": "ja",
        "ui_locale": "ja",
        "label": "日本語",
        "src": "/media/videos/demos/projects-2026-09-14.ja.mp4",
        "captions": "/media/videos/demos/projects-2026-09-14.ja.vtt",
        "captionCode": "ja",
        "note": "",
        "canonical": True,
    }


def test_a_video_without_a_japanese_file_offers_only_english():
    # Arrange
    entry = dict(PUBLISHED_GUIDE)
    entry.pop("ja_url")
    entry.pop("ja_captions")
    # Act
    renditions = languages_for(entry)
    # Assert
    assert [item["code"] for item in renditions] == ["en"]


def test_a_catalog_entry_without_a_video_has_no_renditions():
    # Arrange / Act
    renditions = languages_for({"title": "placeholder"})
    # Assert
    assert renditions == []
    assert default_language(renditions) == ""
    assert default_captions(renditions) == ""


def test_declared_renditions_publish_a_narration_over_another_ui_language():
    # Arrange: the Writer editor is not translated, so the Japanese narration is
    # offered over the English UI as a separate rendition instead of pretending.
    entry = dict(PUBLISHED_GUIDE)
    entry["renditions"] = [
        {"language": "en", "ui_locale": "en",
         "url": "/media/videos/demos/writer-2026-09-14.en.mp4",
         "captions": "/media/videos/demos/writer-2026-09-14.en.vtt"},
        {"language": "ja", "ui_locale": "ja",
         "url": "/media/videos/demos/writer-2026-09-14.ja.mp4",
         "captions": "/media/videos/demos/writer-2026-09-14.ja.vtt"},
        {"language": "ja", "ui_locale": "en",
         "url": "/media/videos/demos/writer-2026-09-14.ui-en.ja.mp4",
         "captions": "/media/videos/demos/writer-2026-09-14.ui-en.ja.vtt",
         "note": "The Writer editor labels are still English."},
    ]
    # Act
    renditions = languages_for(entry)
    # Assert
    assert [item["code"] for item in renditions] == ["en", "ja", "ja@en"]
    alternate = renditions[2]
    assert alternate["captionCode"] == "ja"      # captions follow the narration
    assert alternate["ui_locale"] == "en"        # the screen is English
    assert alternate["canonical"] is False
    assert alternate["note"] == "The Writer editor labels are still English."


def test_declared_renditions_win_over_the_flat_keys():
    # Arrange
    entry = dict(PUBLISHED_GUIDE)
    entry["renditions"] = [
        {"language": "ja", "ui_locale": "ja", "url": "/media/videos/demos/only-ja.mp4"}
    ]
    # Act
    renditions = languages_for(entry)
    # Assert
    assert [item["src"] for item in renditions] == ["/media/videos/demos/only-ja.mp4"]


def test_duplicate_rendition_codes_are_collapsed():
    # Arrange
    entry = {"url": "/media/videos/demos/a.en.mp4"}
    entry["renditions"] = [
        {"language": "en", "ui_locale": "en", "url": "/media/videos/demos/one.mp4"},
        {"language": "en", "ui_locale": "en", "url": "/media/videos/demos/two.mp4"},
    ]
    # Act
    renditions = languages_for(entry)
    # Assert
    assert [item["src"] for item in renditions] == ["/media/videos/demos/one.mp4"]


def test_renditions_without_a_url_are_dropped():
    # Arrange
    entry = {"renditions": [{"language": "en", "ui_locale": "en"}, "not-a-mapping"]}
    # Act
    renditions = languages_for(entry)
    # Assert
    assert renditions == []


def test_a_japanese_visitor_starts_on_the_japanese_narration():
    # Arrange
    renditions = languages_for(PUBLISHED_GUIDE)
    # Act / Assert
    assert default_language(renditions, "ja") == "ja"
    assert default_language(renditions, "ja-jp") == "ja"
    assert default_captions(renditions, "ja") == "ja"


def test_an_english_visitor_starts_on_the_english_narration():
    # Arrange
    renditions = languages_for(PUBLISHED_GUIDE)
    # Act / Assert
    assert default_language(renditions, "en") == "en"
    assert default_language(renditions, "de") == "en"  # no German file: the first one
    assert default_captions(renditions, "en") == "en"


def test_a_language_without_captions_does_not_ask_for_a_missing_track():
    # Arrange
    entry = {"url": "/media/videos/demos/a.en.mp4", "ja_url": "/media/videos/demos/a.ja.mp4"}
    # Act
    renditions = languages_for(entry)
    # Assert
    assert default_captions(renditions, "ja") == ""


def test_rendition_code_keeps_the_canonical_codes_short():
    # Arrange / Act / Assert
    assert rendition_code("ja", "ja") == "ja"
    assert rendition_code("ja", "") == "ja"
    assert rendition_code("ja", "en") == "ja@en"
