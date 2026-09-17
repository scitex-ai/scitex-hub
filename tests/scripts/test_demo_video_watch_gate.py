#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: the human watch gate that publishing has to pass."""

import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_manifest import file_digest  # noqa: E402
from demo_watch_gate import (  # noqa: E402
    MINIMUM_WATCHED_SECONDS,
    gate_path,
    gate_status,
    init_gate,
    load_gate,
    record_watch,
    save_gate,
)


def manifest_for(out_dir: Path, languages=("en", "ja")) -> dict:
    """A manifest shaped like the recorder's, with real files behind each video."""
    renditions = []
    for language in languages:
        video = out_dir / f"demo-2026-09-17.{language}.mp4"
        video.write_bytes(f"video-{language}".encode())
        record = dict(file_digest(video))
        record["role"] = "video"
        renditions.append(
            {
                "language": language,
                "ui_locale": language,
                "canonical": True,
                "viewport": "desktop",
                "duration_seconds": 21.5,
                "files": [record],
            }
        )
    return {
        "schema": "scitex.demo-video.manifest/1",
        "app": "demo",
        "date": "2026-09-17",
        "source": {"commit": "a" * 40},
        "matrix": {"languages": list(languages), "viewports": ["desktop"]},
        "renditions": renditions,
    }


def test_a_fresh_gate_is_not_publishable_and_names_both_languages(tmp_path):
    # Arrange
    manifest = manifest_for(tmp_path)
    # Act
    gate = init_gate(manifest)
    status = gate_status(gate, tmp_path)
    # Assert
    assert gate["required_languages"] == ["en", "ja"]
    assert gate["watches"] == {"en": None, "ja": None}
    assert status["missing"] == ["en", "ja"]
    assert status["publishable"] is False


def test_one_watched_language_is_not_enough(tmp_path):
    # Arrange: only the English video was watched, which is the failure mode the
    # gate exists for — the Japanese rendition is the one nobody reads by default.
    manifest = manifest_for(tmp_path)
    gate = init_gate(manifest)
    record_watch(gate, language="en", watched_by="operator", verdict="pass",
                 watched_seconds=30.0)
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["watched"] == ["en"]
    assert status["missing"] == ["ja"]
    assert status["publishable"] is False


def test_both_languages_watched_publishes(tmp_path):
    # Arrange
    manifest = manifest_for(tmp_path)
    gate = init_gate(manifest)
    for language in ("en", "ja"):
        record_watch(gate, language=language, watched_by="operator", verdict="pass",
                     watched_seconds=30.0, notes="captions and audio checked")
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["missing"] == [] and status["failing"] == []
    assert status["publishable"] is True
    assert gate["watches"]["ja"]["artifact_sha256"] == file_digest(
        tmp_path / "demo-2026-09-17.ja.mp4"
    )["sha256"]


def test_a_render_after_the_watch_invalidates_the_gate(tmp_path):
    # Arrange: the video was re-rendered after it was watched.
    manifest = manifest_for(tmp_path)
    gate = init_gate(manifest)
    for language in ("en", "ja"):
        record_watch(gate, language=language, watched_by="operator", verdict="pass",
                     watched_seconds=30.0)
    (tmp_path / "demo-2026-09-17.ja.mp4").write_bytes(b"a different Japanese render")
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["stale"] == [
        {"language": "ja", "reason": "the file on disk differs from the watched artifact"}
    ]
    assert status["publishable"] is False


def test_a_failed_watch_keeps_the_gate_closed(tmp_path):
    # Arrange
    manifest = manifest_for(tmp_path)
    gate = init_gate(manifest)
    record_watch(gate, language="en", watched_by="operator", verdict="pass",
                 watched_seconds=30.0)
    record_watch(gate, language="ja", watched_by="operator", verdict="fail",
                 watched_seconds=30.0, notes="captions overlap the dock at 390px")
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["failing"] == [{"language": "ja", "verdict": "fail"}]
    assert status["publishable"] is False


def test_a_watch_too_short_to_have_seen_the_video_does_not_count(tmp_path):
    # Arrange
    manifest = manifest_for(tmp_path)
    gate = init_gate(manifest)
    for language in ("en", "ja"):
        record_watch(gate, language=language, watched_by="operator", verdict="pass",
                     watched_seconds=MINIMUM_WATCHED_SECONDS / 2)
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert [entry["verdict"] for entry in status["failing"]] == ["too-short", "too-short"]
    assert status["publishable"] is False


def test_a_watch_of_an_unknown_language_is_rejected(tmp_path):
    # Arrange
    gate = init_gate(manifest_for(tmp_path))
    # Act / Assert
    with pytest.raises(ValueError, match="not a required language"):
        record_watch(gate, language="de", watched_by="operator", verdict="pass",
                     watched_seconds=30.0)


def test_a_watch_without_a_name_is_rejected(tmp_path):
    # Arrange
    gate = init_gate(manifest_for(tmp_path))
    # Act / Assert
    with pytest.raises(ValueError, match="who watched"):
        record_watch(gate, language="en", watched_by="   ", verdict="pass",
                     watched_seconds=30.0)


def test_gate_file_round_trips_next_to_the_render(tmp_path):
    # Arrange
    manifest = manifest_for(tmp_path)
    path = gate_path(tmp_path, "demo", "2026-09-17")
    gate = init_gate(manifest, path=path)
    record_watch(gate, language="en", watched_by="operator", verdict="pass",
                 watched_seconds=30.0)
    # Act
    save_gate(path, gate)
    loaded = load_gate(path)
    # Assert
    assert path.name == "demo-2026-09-17.watch-gate.json"
    assert loaded["watches"]["en"]["watched_by"] == "operator"
    assert loaded["schema"] == "scitex.demo-video.watch-gate/1"
