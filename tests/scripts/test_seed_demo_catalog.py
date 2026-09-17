#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seeding the catalog: idempotent, and refusals are part of the contract."""

import json
import subprocess
import sys
from pathlib import Path

DEMO_VIDEOS = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"


def a_render(tmp_path: Path, app: str = "projects", date: str = "2026-09-17",
             seconds: float = 50.0, tag: str = "r1") -> Path:
    directory = tmp_path / tag
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "scitex.demo-video.manifest/1",
        "app": app,
        "date": date,
        "generated_at": f"{date}T10:00:00Z",
        "titles": {"en": "Create your first project"},
        "source": {"commit": "a" * 40, "branch": "develop", "dirty": False},
        "environment": {"voice": True, "narration_failures": {}},
        "renditions": [{"language": "en", "ui_locale": "en", "viewport": "desktop",
                        "canonical": True, "duration_seconds": seconds,
                        "files": [{"role": "video", "name": f"{app}.en.mp4"}]}],
    }
    (directory / f"{app}-{date}.manifest.json").write_text(json.dumps(manifest),
                                                           encoding="utf-8")
    return directory


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DEMO_VIDEOS / "seed_demo_catalog.py"), *args],
        capture_output=True, text=True, check=False,
    )


def test_seeding_registers_a_draft_and_is_idempotent(tmp_path):
    # Arrange
    catalog = tmp_path / "demos-catalog.json"
    render = a_render(tmp_path)
    # Act
    first = run("--catalog", str(catalog), "--render", f"projects={render}")
    second = run("--catalog", str(catalog), "--render", f"projects={render}")
    # Assert
    assert first.returncode == 0 and second.returncode == 0
    clips = json.loads(catalog.read_text(encoding="utf-8"))["clips"]
    assert len(clips) == 1                      # not duplicated
    assert clips[0]["status"] == "draft"        # never approved by seeding


def test_a_rejected_take_needs_a_reason_and_stays_as_history(tmp_path):
    # Arrange
    catalog = tmp_path / "demos-catalog.json"
    render = a_render(tmp_path)
    # Act: a rejection without a reason is refused outright.
    refused = run("--catalog", str(catalog), "--reject", f"projects={render}")
    accepted = run("--catalog", str(catalog), "--reject", f"projects={render}",
                   "--reason", "workspace stayed dark")
    # Assert
    assert refused.returncode == 1
    assert "needs a --reason" in refused.stderr
    assert accepted.returncode == 0
    clips = json.loads(catalog.read_text(encoding="utf-8"))["clips"]
    assert clips[0]["status"] == "rejected"
    assert clips[0]["rejection"]["reason"] == "workspace stayed dark"
    assert clips[0]["history"][-1]["what"].startswith("rejected")


def test_a_missing_manifest_is_refused_rather_than_silently_skipped(tmp_path):
    # Arrange
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    # Act
    result = run("--catalog", str(tmp_path / "c.json"), "--render", f"projects={empty}")
    # Assert
    assert result.returncode != 0
    assert "no manifest" in (result.stdout + result.stderr)
