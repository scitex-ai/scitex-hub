#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion metadata: what a reviewed render becomes when Docs embeds it."""

import argparse
import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_manifest import file_digest  # noqa: E402
from demo_promotion import (  # noqa: E402
    PROMOTION_SCHEMA,
    build_promotion,
    default_description,
    load_promotion,
    parse_description,
    promoted_assets,
    promotion_for_manifest,
    promotion_path,
    verify_promotion,
    write_promotion,
)


def write_render(out_dir: Path, languages=("en", "ja"), viewport="desktop") -> dict:
    """A manifest plus the real files it describes, shaped like a render's output."""
    renditions = []
    for language in languages:
        files = []
        for role, suffix in (("video", "mp4"), ("captions", "vtt"), ("chapters", "chapters.vtt"),
                             ("transcript", "txt"), ("thumbnail", "thumbnail.png")):
            path = out_dir / f"projects-2026-09-17.{language}.{suffix}"
            path.write_text(f"{language}-{role}", encoding="utf-8")
            record = dict(file_digest(path))
            record["role"] = role
            files.append(record)
        renditions.append({"language": language, "ui_locale": language, "canonical": True,
                           "viewport": viewport, "duration_seconds": 50.6, "cues": 7,
                           "files": files})
    return {
        "app": "projects",
        "date": "2026-09-17",
        "titles": {"en": "Create your first project", "ja": "はじめてのプロジェクトを作る"},
        "source": {"commit": "b" * 40},
        "scenario": {"sha256": "c" * 64},
        "renditions": renditions,
    }


def test_promotion_pins_the_canonical_files_and_their_digests(tmp_path):
    # Arrange
    manifest = write_render(tmp_path)
    # Act
    promotion = build_promotion(
        manifest, promoted_by="operator", hub_version_value="0.20.0a1",
        docs_targets=["/apps/docs/#howto-projects"], embed_key="guide-create-first-project",
        promoted_at="2026-09-17T11:05:00+00:00",
    )
    # Assert
    assert promotion["schema"] == PROMOTION_SCHEMA
    assert promotion["hub_version"] == "0.20.0a1"
    assert promotion["commit"] == "b" * 40
    assert promotion["titles"]["ja"] == "はじめてのプロジェクトを作る"
    assert set(promotion["assets"]) == {"en", "ja"}
    assert promotion["assets"]["en"]["video"]["name"] == "projects-2026-09-17.en.mp4"
    assert promotion["video_sha256"]["ja"] == promotion["assets"]["ja"]["video"]["sha256"]
    assert promotion["assets"]["en"]["duration_seconds"] == 50.6
    assert promotion["leaf_versions"] == {}


def test_promotion_can_version_a_leaf_app_too(tmp_path):
    # Arrange: a Writer guide is not only versioned against the Hub commit.
    manifest = write_render(tmp_path)
    # Act
    promotion = build_promotion(
        manifest, promoted_by="operator", hub_version_value="0.20.0a1", docs_targets=["/x/"],
        leaf_versions={"scitex-writer": "2.43.1"},
    )
    # Assert
    assert promotion["leaf_versions"] == {"scitex-writer": "2.43.1"}


def test_promoted_assets_skip_alternates_and_other_viewports(tmp_path):
    # Arrange: a mobile rendition and an alternate UI-locale one are not what Docs embeds.
    manifest = write_render(tmp_path)
    manifest["renditions"] += [
        {"language": "en", "ui_locale": "en", "canonical": True, "viewport": "mobile",
         "duration_seconds": 21.0, "cues": 4, "files": []},
        {"language": "ja", "ui_locale": "en", "canonical": False, "viewport": "desktop",
         "duration_seconds": 26.0, "cues": 4, "files": []},
    ]
    # Act
    assets = promoted_assets(manifest, "desktop")
    # Assert
    assert sorted(assets) == ["en", "ja"]
    assert all(entry["duration_seconds"] == 50.6 for entry in assets.values())


def test_the_default_description_comes_from_the_render_s_own_words(tmp_path):
    # Arrange: the transcript the recorder wrote, chapter list and all.
    (tmp_path / "projects-2026-09-17.en.txt").write_text(
        "Create your first project\n"
        "\n"
        "Chapters\n"
        "00:00 Home\n"
        "00:03 Create a project\n"
        "\n"
        "1. This is Home, where your apps live.\n",
        encoding="utf-8",
    )
    # Act
    description = default_description(tmp_path, {"app": "projects", "date": "2026-09-17"}, "en")
    # Assert
    assert description == "Create your first project: 00:00 Home; 00:03 Create a project"


def test_a_missing_transcript_yields_no_description(tmp_path):
    # Arrange / Act / Assert
    assert default_description(tmp_path, {"app": "projects", "date": "2026-09-17"}, "ja") == ""


def test_promotion_files_sit_next_to_their_manifest():
    # Arrange
    manifest = Path("/renders/projects-2026-09-17.manifest.json")
    # Act / Assert
    assert promotion_for_manifest(manifest).name == "projects-2026-09-17.promotion.json"
    assert promotion_path(Path("/renders"), "projects", "2026-09-17").name == (
        "projects-2026-09-17.promotion.json"
    )


def test_a_written_promotion_round_trips(tmp_path):
    # Arrange
    manifest = write_render(tmp_path)
    promotion = build_promotion(
        manifest, promoted_by="operator", hub_version_value="0.20.0a1", docs_targets=["/x/"],
        promoted_at="2026-09-17T11:05:00+00:00",
    )
    path = write_promotion(promotion_path(tmp_path, "projects", "2026-09-17"), promotion)
    # Act
    loaded = load_promotion(path)
    # Assert
    assert loaded == promotion


def test_verification_passes_for_the_files_it_pinned(tmp_path):
    # Arrange
    manifest = write_render(tmp_path)
    promotion = build_promotion(manifest, promoted_by="operator", hub_version_value="0.20.0a1",
                                docs_targets=["/x/"])
    # Act / Assert
    assert verify_promotion(promotion, tmp_path) == []


def test_verification_notices_a_replaced_or_deleted_asset(tmp_path):
    # Arrange: the whole point of pinning is that an embed cannot drift.
    manifest = write_render(tmp_path)
    promotion = build_promotion(manifest, promoted_by="operator", hub_version_value="0.20.0a1",
                                docs_targets=["/x/"])
    (tmp_path / "projects-2026-09-17.ja.mp4").write_text("re-encoded by hand", encoding="utf-8")
    (tmp_path / "projects-2026-09-17.en.vtt").unlink()
    # Act
    problems = verify_promotion(promotion, tmp_path)
    # Assert
    assert any("ja/video" in problem for problem in problems)
    assert any("en/captions" in problem for problem in problems)


def test_description_arguments_are_validated():
    # Arrange / Act / Assert
    assert parse_description("en=Create a project") == ("en", "Create a project")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_description("no-equals-sign")
