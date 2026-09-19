#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The copy-only DaVinci canary: staging, and the comparison that proves a derivative.

Real files and real ffmpeg throughout: the thing under test is whether a derivative
matches the source and whether the source survived the pass, and neither question can
be answered by a mock.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from davinci_canary import (  # noqa: E402
    CanaryError,
    canonical_rendition,
    count_cues,
    stage,
    stage_plan,
    verify,
)
from demo_manifest import file_digest, load_manifest  # noqa: E402
from demo_tools import find_media_tools  # noqa: E402

TOOLS = find_media_tools()
pytestmark = pytest.mark.skipif(not TOOLS.has_ffmpeg, reason="ffmpeg is required")

CAPTIONS = (
    "WEBVTT\n"
    "\n"
    "1\n"
    "00:00:00.000 --> 00:00:01.000\n"
    "First line\n"
    "\n"
    "2\n"
    "00:00:01.000 --> 00:00:02.000\n"
    "Second line\n"
)


def make_render(tmp_path: Path, duration: float = 2.0) -> Path:
    """A miniature render: a real MP4, captions, chapters, and a matching manifest."""
    render = tmp_path / "render"
    render.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc=size=320x180:rate=10:duration={duration}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(render / "projects-2026-09-17.en.mp4")],
        check=True,
    )
    for name, body in (("projects-2026-09-17.en.vtt", CAPTIONS),
                       ("projects-2026-09-17.en.chapters.vtt", CAPTIONS),
                       ("projects-2026-09-17.en.txt", "A demo\n\n1. First line\n")):
        (render / name).write_text(body, encoding="utf-8")
    files = []
    for role, name in (("video", "projects-2026-09-17.en.mp4"),
                       ("captions", "projects-2026-09-17.en.vtt"),
                       ("chapters", "projects-2026-09-17.en.chapters.vtt"),
                       ("transcript", "projects-2026-09-17.en.txt")):
        record = dict(file_digest(render / name))
        record["role"] = role
        files.append(record)
    manifest = {
        "schema": "scitex.demo-video.manifest/1",
        "app": "projects",
        "date": "2026-09-17",
        "source": {"commit": "b" * 40},
        "renditions": [
            {"language": "en", "ui_locale": "en", "canonical": True, "viewport": "desktop",
             "duration_seconds": duration, "cues": 2, "theme": "light", "files": files}
        ],
    }
    path = render / "projects-2026-09-17.manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def test_staging_copies_the_rendition_and_extracts_its_audio(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    render = manifest.parent
    stage_dir = tmp_path / "canary"
    # Act
    result = stage(manifest, render, stage_dir, TOOLS)
    # Assert
    assert result["source_unchanged"] is True
    assert (stage_dir / "video.mp4").is_file()
    assert (stage_dir / "captions.vtt").is_file()
    assert (stage_dir / "narration.wav").stat().st_size > 0
    assert (stage_dir / "RUNBOOK.md").is_file()
    expected = json.loads((stage_dir / "expected.json").read_text())
    assert expected["theme"] == "light"
    assert expected["cues"] == 2
    assert expected["duration_seconds"] == 2.0
    assert "never" in (stage_dir / "RUNBOOK.md").read_text().lower()


def test_staging_leaves_every_source_digest_exactly_as_the_manifest_recorded_it(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    render = manifest.parent
    before = {path.name: file_digest(path)["sha256"] for path in render.iterdir()}
    # Act
    stage(manifest, render, tmp_path / "canary", TOOLS)
    # Assert: a canary that edits what it is checking is worse than no canary.
    after = {path.name: file_digest(path)["sha256"] for path in render.iterdir()}
    assert after == before


def test_staging_refuses_to_write_inside_the_render_directory(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    # Act / Assert
    with pytest.raises(CanaryError, match="outside the render directory"):
        stage_plan(load_manifest(manifest), manifest.parent, manifest.parent / "canary")


def test_a_faithful_derivative_verifies(tmp_path):
    # Arrange: what a Resolve render of the staged copies should look like.
    manifest = make_render(tmp_path)
    stage_dir = tmp_path / "canary"
    stage(manifest, manifest.parent, stage_dir, TOOLS)
    derivative = stage_dir / "derivative"
    derivative.mkdir()
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / "video.mp4"),
         "-i", str(stage_dir / "narration.wav"), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(derivative / "projects-canary.mp4")],
        check=True,
    )
    (derivative / "projects-canary.vtt").write_text(CAPTIONS, encoding="utf-8")
    # Act
    result = verify(manifest, manifest.parent, derivative / "projects-canary.mp4", TOOLS)
    # Assert
    assert result["problems"] == []
    assert result["verified"] is True
    assert result["checks"]["has_audio"] is True
    assert result["checks"]["duration_within_tolerance"] is True
    assert result["checks"]["cues_match"] is True
    assert result["checks"]["source_untouched"] is True


def test_a_derivative_that_lost_its_audio_is_refused(tmp_path):
    # Arrange: the failure mode that would otherwise ship a silent "finished" video.
    manifest = make_render(tmp_path)
    stage_dir = tmp_path / "canary"
    stage(manifest, manifest.parent, stage_dir, TOOLS)
    silent = stage_dir / "derivative-silent.mp4"
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / "video.mp4"),
         "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent)],
        check=True,
    )
    # Act
    result = verify(manifest, manifest.parent, silent, TOOLS)
    # Assert
    assert result["verified"] is False
    assert any("no audio stream" in problem for problem in result["problems"])


def test_a_truncated_derivative_is_refused(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    stage_dir = tmp_path / "canary"
    stage(manifest, manifest.parent, stage_dir, TOOLS)
    short = stage_dir / "derivative-short.mp4"
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / "video.mp4"),
         "-t", "0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(short)],
        check=True,
    )
    # Act
    result = verify(manifest, manifest.parent, short, TOOLS)
    # Assert
    assert result["verified"] is False
    assert any("duration" in problem for problem in result["problems"])


def test_a_derivative_whose_captions_dropped_cues_is_refused(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    stage_dir = tmp_path / "canary"
    stage(manifest, manifest.parent, stage_dir, TOOLS)
    derivative = stage_dir / "derivative"
    derivative.mkdir()
    video = derivative / "canary.mp4"
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / "video.mp4"),
         "-c", "copy", str(video)],
        check=True,
    )
    (derivative / "canary.vtt").write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nOnly\n",
                                           encoding="utf-8")
    # Act
    result = verify(manifest, manifest.parent, video, TOOLS)
    # Assert
    assert result["verified"] is False
    assert any("cues" in problem for problem in result["problems"])


def test_a_source_file_changed_during_the_canary_is_reported(tmp_path):
    # Arrange: the canary's first duty is to leave the artifact alone.
    manifest = make_render(tmp_path)
    stage_dir = tmp_path / "canary"
    stage(manifest, manifest.parent, stage_dir, TOOLS)
    derivative = stage_dir / "derivative"
    derivative.mkdir()
    subprocess.run(
        [TOOLS.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / "video.mp4"),
         "-c", "copy", str(derivative / "canary.mp4")],
        check=True,
    )
    (manifest.parent / "projects-2026-09-17.en.vtt").write_text(
        CAPTIONS + "\n3\n00:00:02.000 --> 00:00:03.000\nEdited by hand\n", encoding="utf-8")
    # Act
    result = verify(manifest, manifest.parent, derivative / "canary.mp4", TOOLS)
    # Assert
    assert result["verified"] is False
    assert result["checks"]["source_untouched"] is False
    assert any("source captions file changed" in problem for problem in result["problems"])


def test_a_missing_derivative_is_reported_not_crashed(tmp_path):
    # Arrange
    manifest = make_render(tmp_path)
    # Act
    result = verify(manifest, manifest.parent, tmp_path / "absent.mp4", TOOLS)
    # Assert
    assert result["verified"] is False
    assert "does not exist" in result["problems"][0]


def test_the_canonical_rendition_is_the_one_a_canary_works_on(tmp_path):
    # Arrange
    manifest = load_manifest(make_render(tmp_path))
    # Act / Assert
    assert canonical_rendition(manifest, "en", "desktop")["language"] == "en"
    with pytest.raises(CanaryError, match="no canonical ja/desktop"):
        canonical_rendition(manifest, "ja", "desktop")


def test_cue_counting_is_a_timing_line_count(tmp_path):
    # Arrange
    path = tmp_path / "x.vtt"
    path.write_text(CAPTIONS, encoding="utf-8")
    # Act / Assert
    assert count_cues(path) == 2
    assert count_cues(tmp_path / "missing.vtt") == 0
