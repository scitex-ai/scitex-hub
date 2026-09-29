#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The clip library's rules: nothing approves itself, nothing rejected disappears.

The workflow the operator set is a sequence of claims about who did what, so the tests
are about refusals as much as about success: a render arrives as Draft, a person moves it
to Approved, and a rejected clip stays in the catalog instead of vanishing.
"""

import json
import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from clip_registry import (  # noqa: E402
    ClipError, approve, load_catalog, register, reject, summary,
)


def write_manifest(tmp_path: Path, *, app="projects", seconds=50.6, language="en",
                   narration_failures=None, theme_verified=None, defect_note=""):
    """A manifest on disk as a render would leave one."""
    manifest = {
        "schema": "scitex.demo-video.manifest/1",
        "app": app,
        "date": "2026-09-17",
        "generated_at": "2026-09-17T10:00:00Z",
        "titles": {language: f"{app} guide"},
        "source": {"commit": "f" * 40, "branch": "develop", "dirty": False},
        "environment": {"voice": True, "narration_failures": narration_failures or {},
                        "theme": "light" if theme_verified is not None else "",
                        "theme_verified": theme_verified},
        "renditions": [{"language": language, "ui_locale": language, "viewport": "desktop",
                        "canonical": True, "duration_seconds": seconds,
                        "files": [{"role": "video", "name": f"{app}.{language}.mp4"}]}],
    }
    path = tmp_path / f"{app}-{defect_note or 'r1'}.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_a_render_arrives_as_draft_with_its_commit_date_and_defects(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    manifest = write_manifest(tmp_path, seconds=20.0)   # under the 30s clip budget
    # Act
    clip = register(catalog, manifest, queue_item="first-project")
    # Assert
    assert clip["status"] == "draft"
    assert clip["dev_commit"] == "f" * 40
    assert clip["date"] == "2026-09-17"
    assert clip["queue_item"] == "first-project"
    assert any("30s clip budget" in defect for defect in clip["defects"])
    assert clip["watch"] is None


def test_a_clip_within_the_budget_has_no_budget_defect(tmp_path):
    # Arrange / Act
    clip = register(tmp_path / "catalog.json", write_manifest(tmp_path, seconds=50.6))
    # Assert
    assert not [d for d in clip["defects"] if "clip budget" in d]


def test_registering_the_same_render_twice_does_not_approve_it(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    manifest = write_manifest(tmp_path)
    # Act
    first = register(catalog, manifest)
    second = register(catalog, manifest)
    # Assert: a Draft that arrives twice is still a Draft, and it is the same clip.
    assert first["id"] == second["id"]
    assert second["status"] == "draft"
    assert len(load_catalog(catalog)["clips"]) == 1


def test_a_re_render_is_a_new_clip_and_the_rejected_one_stays(tmp_path):
    # Arrange: one render, rejected, then a second render of the same scenario.
    catalog = tmp_path / "catalog.json"
    first = register(catalog, write_manifest(tmp_path, defect_note="take1"))
    reject(catalog, first["id"], by="operator", reason="interface was dark")
    # Act
    # A real re-render differs in its bytes and therefore its manifest digest.
    second = register(catalog, write_manifest(tmp_path, seconds=55.0, defect_note="take2"))
    # Assert
    assert second["id"] != first["id"]
    clips = {clip["id"]: clip for clip in load_catalog(catalog)["clips"]}
    assert clips[first["id"]]["status"] == "rejected"      # history, not deleted
    assert clips[first["id"]]["rejection"]["reason"] == "interface was dark"
    assert clips[second["id"]]["status"] == "draft"


def test_approval_needs_a_named_watcher_and_a_watched_duration(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    clip = register(catalog, write_manifest(tmp_path))
    # Act / Assert
    with pytest.raises(ClipError):
        approve(catalog, clip["id"], by="", watched_seconds=60.0)
    with pytest.raises(ClipError):
        approve(catalog, clip["id"], by="operator", watched_seconds=0)
    assert load_catalog(catalog)["clips"][0]["status"] == "draft"
    approved = approve(catalog, clip["id"], by="operator", watched_seconds=52.0,
                       notes="watched both renditions")
    assert approved["status"] == "approved"
    assert approved["watch"]["by"] == "operator"
    assert [entry["what"] for entry in approved["history"]] == [
        "registered as draft", "approved after a watch"]


def test_a_rejected_clip_is_history_and_cannot_be_approved(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    clip = register(catalog, write_manifest(tmp_path))
    reject(catalog, clip["id"], by="operator", reason="wrong scenario in frame")
    # Act / Assert
    with pytest.raises(ClipError):
        approve(catalog, clip["id"], by="operator", watched_seconds=60.0)
    with pytest.raises(ClipError):
        reject(catalog, clip["id"], by="", reason="")
    assert load_catalog(catalog)["clips"][0]["status"] == "rejected"


def test_a_failed_narration_and_an_unverified_theme_are_both_defects(tmp_path):
    # Arrange
    manifest = write_manifest(tmp_path, narration_failures={"ja": "gTTS failed"},
                              theme_verified=False)
    # Act
    clip = register(tmp_path / "catalog.json", manifest)
    # Assert
    joined = " | ".join(clip["defects"])
    assert "narration failed for ja" in joined
    assert "theme light was requested and not verified" in joined


def test_the_summary_says_what_is_waiting_on_a_person(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    register(catalog, write_manifest(tmp_path, defect_note="take1"))
    with_defect = register(catalog, write_manifest(tmp_path, seconds=20.0,
                                                   defect_note="take2"))
    approve(catalog, with_defect["id"], by="operator", watched_seconds=45.0)
    # Act
    counts = summary(load_catalog(catalog))
    # Assert
    assert counts["clips"] == 2
    assert counts["by_status"]["draft"] == 1
    assert counts["by_status"]["approved"] == 1
    assert counts["awaiting_a_watch"] == 1


def test_a_catalog_that_is_not_a_catalog_is_refused(tmp_path):
    # Arrange
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"schema": "something.else/1", "clips": []}), encoding="utf-8")
    # Act / Assert
    with pytest.raises(ClipError):
        load_catalog(catalog)
