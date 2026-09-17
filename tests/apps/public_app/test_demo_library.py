#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The staff library's card rules: derived visibility, watch state, media names.

No Django here: the module under test reads files and returns dicts, so the rules
that decide what the team may publish are testable without a database or a browser.
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "apps" / "infra" / "public_app" / "demo_library.py"


def load_module():
    spec = importlib.util.spec_from_file_location("demo_library", MODULE_PATH)
    assert spec is not None and spec.loader is not None, MODULE_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_library"] = module
    spec.loader.exec_module(module)
    return module


library = load_module()


def file_record(name: str, digest: str = "a" * 64, size: int = 1000) -> dict:
    return {"name": name, "sha256": digest, "bytes": size, "missing": False}


def manifest_for(base: str = "projects-2026-09-17", languages=("en", "ja")) -> dict:
    """A manifest whose app and date come from its own file stem."""
    date = base[-10:]
    app = base[: -len(date) - 1] if len(base) > 11 else base
    renditions = []
    for language in languages:
        renditions.append({
            "language": language,
            "ui_locale": language,
            "canonical": True,
            "viewport": "desktop",
            "duration_seconds": 50.6,
            "narration_seconds": 21.4,
            "cues": 7,
            "files": [
                dict(file_record(f"{base}.{language}.mp4"), role="video"),
                dict(file_record(f"{base}.{language}.vtt"), role="captions"),
                dict(file_record(f"{base}.{language}.chapters.vtt"), role="chapters"),
                dict(file_record(f"{base}.{language}.txt"), role="transcript"),
                dict(file_record(f"{base}.{language}.thumbnail.png"), role="thumbnail"),
                dict(file_record(f"{base}.{language}.webm"), role="raw"),
            ],
        })
    return {
        "schema": "scitex.demo-video.manifest/1",
        "app": app,
        "date": date,
        "generated_at": "2026-09-17T10:44:07+00:00",
        "titles": {"en": "Create your first project", "ja": "はじめてのプロジェクトを作る"},
        "source": {"branch": "feat/bilingual-first-use-tutorial-videos", "commit": "b" * 40,
                   "dirty": False},
        "environment": {"voice": True, "narration_failures": {}, "caption_font_available": True},
        "renditions": renditions,
    }


def gate_for(languages=("en", "ja"), verdict="pass", artifact_digest="a" * 64,
             watch_digest=None) -> dict:
    return {
        "schema": "scitex.demo-video.watch-gate/1",
        "app": "projects",
        "date": "2026-09-17",
        "required_languages": list(languages),
        "artifacts": {language: {"name": f"projects-2026-09-17.{language}.mp4",
                                 "sha256": artifact_digest, "bytes": 1000}
                      for language in languages},
        "watches": {
            language: {
                "watched_by": "operator",
                "watched_at": "2026-09-17T11:00:00+00:00",
                "verdict": verdict,
                "watched_seconds": 60.0,
                "artifact_sha256": watch_digest or artifact_digest,
            }
            for language in languages
        },
    }


def promotion_for(embed_key="guide-create-first-project", docs=("/apps/docs/#howto-projects",),
                  hashes=None) -> dict:
    return {
        "schema": "scitex.demo-video.promotion/1",
        "app": "projects",
        "date": "2026-09-17",
        "hub_version": "0.20.0a1",
        "leaf_versions": {},
        "promoted_by": "operator",
        "promoted_at": "2026-09-17T11:05:00+00:00",
        "embed_key": embed_key,
        "docs_targets": list(docs),
        "descriptions": {"en": "Create your first project"},
        "video_sha256": hashes if hashes is not None else {"en": "a" * 64, "ja": "a" * 64},
    }


def write_library(tmp_path: Path, manifest=None, gate=None, promotion=None) -> Path:
    """A library directory holding a manifest and whichever sidecars are given.

    File names come from the manifest's own app and date, so two captures can live
    in one directory — which is the case the index has to sort and count.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = manifest if manifest is not None else manifest_for()
    stem = f"{manifest['app']}-{manifest['date']}"
    (tmp_path / f"{stem}.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for suffix, payload in (("watch-gate", gate), ("promotion", promotion)):
        if payload is not None:
            (tmp_path / f"{stem}.{suffix}.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_a_render_without_sidecars_is_a_private_draft(tmp_path):
    # Arrange: just recorded, nobody has watched it, nothing is promoted.
    directory = write_library(tmp_path / "lib")
    # Act
    index = library.library_index(directory)
    # Assert
    entry = index["entries"][0]
    assert entry["visibility"] == "private-draft"
    assert entry["watch"]["state"] == "no-gate"
    assert entry["hub_version"] == ""
    assert index["counts"]["private-draft"] == 1


def test_the_card_carries_the_version_commit_and_both_languages(tmp_path):
    # Arrange
    directory = write_library(tmp_path / "lib", gate=gate_for(), promotion=promotion_for())
    # Act
    entry = library.library_index(directory)["entries"][0]
    # Assert
    assert entry["app"] == "projects"
    assert entry["hub_version"] == "0.20.0a1"
    assert entry["commit"] == "b" * 40
    assert entry["languages"] == ["en", "ja"]
    assert entry["viewports"] == ["desktop"]
    assert entry["narrated"] is True
    assert [row["duration_seconds"] for row in entry["renditions"]] == [50.6, 50.6]
    assert entry["renditions"][0]["files"]["chapters"] == "projects-2026-09-17.en.chapters.vtt"


def test_both_languages_watched_makes_it_reviewed_and_promotion_makes_it_public_ready(tmp_path):
    # Arrange: watched but not promoted, then promoted.
    unwatched = write_library(tmp_path / "a", gate=gate_for())
    promoted = write_library(tmp_path / "b", gate=gate_for(), promotion=promotion_for())
    # Act / Assert
    assert library.library_index(unwatched)["entries"][0]["visibility"] == "reviewed"
    assert library.library_index(promoted)["entries"][0]["visibility"] == "public-ready"


def test_one_watched_language_stays_a_draft(tmp_path):
    # Arrange: English watched, Japanese not — the publishing rule from the spec.
    gate = gate_for()
    gate["watches"]["ja"] = None
    directory = write_library(tmp_path / "lib", gate=gate)
    # Act
    entry = library.library_index(directory)["entries"][0]
    # Assert
    assert entry["watch"]["state"] == "partial"
    assert entry["watch"]["missing"] == ["ja"]
    assert entry["visibility"] == "private-draft"


def test_a_failed_watch_stays_a_draft_and_says_which_language(tmp_path):
    # Arrange
    gate = gate_for(verdict="fail")
    directory = write_library(tmp_path / "lib", gate=gate)
    # Act
    entry = library.library_index(directory)["entries"][0]
    # Assert
    assert entry["watch"]["state"] == "failed"
    assert entry["watch"]["failing"] == ["en", "ja"]
    assert entry["visibility"] == "private-draft"


def test_a_render_after_the_watch_is_not_reviewed(tmp_path):
    # Arrange: the artifact digest moved after the watch (a re-render).
    gate = gate_for(artifact_digest="c" * 64, watch_digest="a" * 64)
    directory = write_library(tmp_path / "lib", gate=gate)
    # Act
    entry = library.library_index(directory)["entries"][0]
    # Assert
    assert entry["watch"]["state"] == "stale"
    assert entry["watch"]["stale"] == ["en", "ja"]
    assert entry["visibility"] == "private-draft"


def test_promotion_without_an_embed_target_is_not_public_ready(tmp_path):
    # Arrange: described, but with no docs page and no pinned digests.
    directory = write_library(
        tmp_path / "lib", gate=gate_for(),
        promotion=promotion_for(embed_key="", docs=(), hashes={}),
    )
    # Act
    entry = library.library_index(directory)["entries"][0]
    # Assert
    assert entry["visibility"] == "reviewed"
    assert entry["promotion"]["promoted"] is False


def test_a_manifest_for_another_schema_is_ignored(tmp_path):
    # Arrange: a future schema must not be half-read by this code.
    manifest = manifest_for()
    manifest["schema"] = "scitex.demo-video.manifest/2"
    directory = write_library(tmp_path / "lib", manifest=manifest)
    # Act
    index = library.library_index(directory)
    # Assert
    assert index["entries"] == []
    assert index["total"] == 0


def test_media_names_lists_every_file_once(tmp_path):
    # Arrange
    directory = write_library(tmp_path / "lib")
    entry = library.library_index(directory)["entries"][0]
    # Act
    names = library.media_names(entry)
    # Assert
    assert len(names) == len(set(names))
    assert "projects-2026-09-17.en.mp4" in names
    assert "projects-2026-09-17.ja.chapters.vtt" in names
    assert all(name.endswith((".mp4", ".vtt", ".txt", ".png", ".webm")) for name in names)


def test_the_index_counts_by_visibility_and_sorts_newest_first(tmp_path):
    # Arrange: two captures; only the newer one is reviewed.
    older = manifest_for("projects-2026-09-16")
    directory = write_library(tmp_path / "lib", manifest=older)
    write_library(
        directory, manifest=manifest_for("projects-2026-09-17"), gate=gate_for(),
    )
    # Act
    index = library.library_index(directory)
    # Assert
    assert [entry["date"] for entry in index["entries"]] == ["2026-09-17", "2026-09-16"]
    assert index["counts"]["reviewed"] == 1
    assert index["counts"]["private-draft"] == 1
    assert index["total"] == 2
