#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The human watch gate, and the ways an unreviewed video used to get through it.

Each case below is one of the ways the gate failed open before the review: a gate that
named no manifest, an artifact record with no digest, a missing file, a mobile
rendition standing in for the published one, a gate paired with another render's
files, and a `record` command that crashed after writing the file it had just changed.
The gate now answers "not publishable" to every one of them, and says why.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_manifest import file_digest  # noqa: E402
from demo_watch_gate import (  # noqa: E402
    MINIMUM_WATCHED_SECONDS,
    GateError,
    gate_path,
    gate_status,
    init_gate,
    load_gate,
    record_watch,
    save_gate,
)


def write_manifest(out_dir: Path, languages=("en", "ja"), viewport: str = "desktop",
                   commit: str = "a" * 40, date: str = "2026-09-17") -> dict:
    """A manifest shaped like the recorder's, with real files behind each video."""
    renditions = []
    for language in languages:
        video = out_dir / f"demo-{date}.{language}.mp4"
        video.write_bytes(f"video-{language}-{viewport}".encode())
        record = dict(file_digest(video))
        record["role"] = "video"
        renditions.append(
            {
                "language": language,
                "ui_locale": language,
                "canonical": True,
                "viewport": viewport,
                "duration_seconds": 21.5,
                "files": [record],
            }
        )
    manifest = {
        "schema": "scitex.demo-video.manifest/1",
        "app": "demo",
        "date": date,
        "source": {"commit": commit},
        "matrix": {"languages": list(languages), "viewports": [viewport]},
        "renditions": renditions,
    }
    (out_dir / f"demo-{date}.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def watched_gate(out_dir: Path, manifest: dict, **kwargs) -> dict:
    """A gate for that manifest, with every language watched and passing."""
    gate = init_gate(manifest, **kwargs)
    for language in gate["required_languages"]:
        record_watch(gate, language=language, watched_by="operator", verdict="pass",
                     watched_seconds=30.0)
    return gate


def test_a_fresh_gate_is_not_publishable_and_names_both_languages(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
    # Act
    gate = init_gate(manifest)
    status = gate_status(gate, tmp_path)
    # Assert
    assert gate["required_languages"] == ["en", "ja"]
    assert gate["watches"] == {"en": None, "ja": None}
    assert status["missing"] == ["en", "ja"]
    assert status["publishable"] is False


def test_both_languages_watched_against_the_current_files_publishes(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["missing"] == [] and status["failing"] == [] and status["problems"] == []
    assert status["publishable"] is True
    assert gate["watches"]["ja"]["artifact_sha256"] == file_digest(
        tmp_path / "demo-2026-09-17.ja.mp4"
    )["sha256"]


def test_one_watched_language_is_not_enough(tmp_path):
    # Arrange: only English watched — the failure mode the gate exists for.
    manifest = write_manifest(tmp_path)
    gate = init_gate(manifest)
    record_watch(gate, language="en", watched_by="operator", verdict="pass",
                 watched_seconds=30.0)
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["watched"] == ["en"]
    assert status["missing"] == ["ja"]
    assert status["publishable"] is False


def test_a_gate_whose_video_files_are_missing_is_not_publishable(tmp_path):
    # Arrange: the fail-open case — an "approved" gate over files that do not exist.
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    (tmp_path / "demo-2026-09-17.ja.mp4").unlink()
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("gone" in entry["reason"] for entry in status["stale"])


def test_a_render_after_the_watch_invalidates_the_gate(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    (tmp_path / "demo-2026-09-17.ja.mp4").write_bytes(b"a different Japanese render")
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("differs from the watched artifact" in entry["reason"] for entry in status["stale"])


def test_a_gate_without_proof_of_the_artifact_cannot_publish(tmp_path):
    # Arrange: artifacts stripped of their digest — nothing to verify against.
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    for artifact in gate["artifacts"].values():
        artifact["sha256"] = ""
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("no digest" in problem for problem in status["problems"])


def test_an_empty_gate_cannot_publish(tmp_path):
    # Arrange: a gate that requires nothing gates nothing.
    gate = {"schema": "scitex.demo-video.watch-gate/1", "app": "demo", "date": "2026-09-17",
            "required_languages": [], "artifacts": {}, "watches": {}}
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("requires no languages" in problem for problem in status["problems"])


def test_a_gate_for_another_render_is_not_publishable(tmp_path):
    # Arrange: the gate names a manifest that recorded different bytes.
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    other = write_manifest(tmp_path, commit="b" * 40)
    for rendition in other["renditions"]:
        for record in rendition["files"]:
            record["sha256"] = "c" * 64
    (tmp_path / "demo-2026-09-17.manifest.json").write_text(json.dumps(other), encoding="utf-8")
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("different video" in entry["reason"] for entry in status["stale"])


def test_a_mobile_rendition_never_stands_in_for_the_published_one(tmp_path):
    # Arrange: keying artifacts by language alone let mobile overwrite desktop.
    manifest = write_manifest(tmp_path)
    manifest["renditions"].append(
        {"language": "en", "ui_locale": "en", "canonical": True, "viewport": "mobile",
         "duration_seconds": 21.0, "files": [dict(file_digest(
             (tmp_path / "demo-2026-09-17.en.mp4")), role="video")]}
    )
    # Act
    gate = init_gate(manifest)
    # Assert: the gate's artifact is the desktop file, and it is named as such.
    assert gate["artifacts"]["en"]["viewport"] == "desktop"
    assert gate["artifacts"]["en"]["name"] == "demo-2026-09-17.en.mp4"


def test_a_non_manifest_cannot_produce_a_gate(tmp_path):
    # Arrange
    (tmp_path / "not-a-manifest.json").write_text('{"schema": "other/1"}', encoding="utf-8")
    # Act / Assert
    with pytest.raises(GateError, match="not a render manifest"):
        init_gate({"schema": "other/1"})


def test_a_manifest_without_a_video_cannot_produce_a_gate(tmp_path):
    # Arrange: reporting a language whose video is absent would gate nothing.
    manifest = write_manifest(tmp_path, languages=("en",))
    manifest["renditions"] = []
    # Act / Assert
    with pytest.raises(GateError, match="no video for"):
        init_gate(manifest)


def test_without_a_render_directory_the_gate_says_unverified_not_publishable(tmp_path):
    # Arrange: a gate alone cannot prove the files are still there.
    manifest = write_manifest(tmp_path)
    gate = watched_gate(tmp_path, manifest)
    # Act
    status = gate_status(gate, None)
    # Assert
    assert status["publishable"] is False
    assert any("unverified" in entry["reason"] for entry in status["stale"])


def test_a_failed_watch_keeps_the_gate_closed(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
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
    manifest = write_manifest(tmp_path)
    gate = init_gate(manifest)
    for language in ("en", "ja"):
        record_watch(gate, language=language, watched_by="operator", verdict="pass",
                     watched_seconds=MINIMUM_WATCHED_SECONDS / 2)
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert [entry["verdict"] for entry in status["failing"]] == ["too-short", "too-short"]
    assert status["publishable"] is False


def test_a_watch_of_an_unknown_language_or_without_a_name_is_rejected(tmp_path):
    # Arrange
    gate = init_gate(write_manifest(tmp_path))
    # Act / Assert
    with pytest.raises(ValueError, match="not a required language"):
        record_watch(gate, language="de", watched_by="operator", verdict="pass",
                     watched_seconds=30.0)
    with pytest.raises(ValueError, match="who watched"):
        record_watch(gate, language="en", watched_by="   ", verdict="pass",
                     watched_seconds=30.0)


def test_a_gate_file_round_trips_next_to_the_render(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
    path = gate_path(tmp_path, "demo", "2026-09-17")
    gate = init_gate(manifest, path=path)
    record_watch(gate, language="en", watched_by="operator", verdict="pass",
                 watched_seconds=30.0)
    save_gate(path, gate)
    # Act
    loaded = load_gate(path)
    # Assert
    assert path.name == "demo-2026-09-17.watch-gate.json"
    assert loaded["watches"]["en"]["watched_by"] == "operator"
    assert loaded["schema"] == "scitex.demo-video.watch-gate/1"


def test_the_record_command_does_not_crash_after_writing(tmp_path):
    # Arrange: the reviewed defect — `record` read args.out_dir without having it, and
    # died after saving the file it had just mutated.
    manifest = write_manifest(tmp_path)
    path = gate_path(tmp_path, "demo", "2026-09-17")
    init_gate(manifest, path=path)
    # Act
    result = subprocess.run(
        [sys.executable, str(DEMO_VIDEOS_DIR / "demo_watch_gate.py"), "record", str(path),
         "--language", "en", "--by", "operator", "--watched-seconds", "30"],
        capture_output=True, text=True, check=False,
    )
    # Assert
    assert result.returncode == 0, result.stderr[-400:]
    assert load_gate(path)["watches"]["en"]["watched_by"] == "operator"


def test_the_status_command_exits_nonzero_for_an_unwatched_gate(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path)
    path = gate_path(tmp_path, "demo", "2026-09-17")
    init_gate(manifest, path=path)
    # Act
    result = subprocess.run(
        [sys.executable, str(DEMO_VIDEOS_DIR / "demo_watch_gate.py"), "status", str(path),
         "--out-dir", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    # Assert
    assert result.returncode == 1
    assert json.loads(result.stdout)["publishable"] is False


def test_the_init_command_refuses_a_foreign_manifest_without_writing(tmp_path):
    # Arrange
    foreign = tmp_path / "foreign.json"
    foreign.write_text('{"schema": "other/1", "app": "x", "date": "2026-09-17"}',
                       encoding="utf-8")
    # Act
    result = subprocess.run(
        [sys.executable, str(DEMO_VIDEOS_DIR / "demo_watch_gate.py"), "init", str(foreign),
         "--out-dir", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    # Assert
    assert result.returncode == 4
    assert not (tmp_path / "x-2026-09-17.watch-gate.json").exists()


def test_a_gate_for_another_schema_is_refused(tmp_path):
    # Arrange
    gate = {"schema": "scitex.demo-video.watch-gate/9", "required_languages": ["en"]}
    # Act
    status = gate_status(gate, tmp_path)
    # Assert
    assert status["publishable"] is False
    assert any("not a watch gate" in problem for problem in status["problems"])
