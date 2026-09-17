#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reviewed library blockers: replaced bytes, borrowed sidecars, symlinked manifests.

The review reproduced three ways an asset could carry a state it had not earned: a
video replaced by hand while its approval survived, a gate or promotion file written
for a different render of the same app sitting next to this one by file name, and a
manifest symlinked from outside the library root appearing in the index. Each is a
regression here.
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


def write_render(directory: Path, *, language: str = "en", video: bytes = b"real video"):
    """A render on disk: the video, a manifest recording its digest, a gate, promotion."""
    directory.mkdir(parents=True, exist_ok=True)
    name = f"x.{language}.mp4"
    (directory / name).write_bytes(video)
    digest = library.sha256_file(directory / name)
    manifest = {
        "schema": library.MANIFEST_SCHEMA,
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
                    {"role": "video", "name": name, "sha256": digest, "size": len(video)}
                ],
            }
        ],
    }
    manifest_path = directory / "x.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, manifest, digest


def write_gate(manifest_path: Path, manifest: dict, digest: str, *, app="projects",
               date="2026-09-17", commit="b" * 40, language="en", gate_digest=None):
    gate = {
        "schema": library.WATCH_GATE_SCHEMA,
        "manifest": {"app": app, "date": date, "commit": commit},
        "required_languages": [language],
        "artifacts": {language: {"sha256": gate_digest or digest, "viewport": "desktop"}},
        "watches": {
            language: {
                "by": "a person", "verdict": "pass", "watched_seconds": 60.0,
                "artifact_sha256": gate_digest or digest,
            }
        },
    }
    path = manifest_path.with_name(manifest_path.name.replace(".manifest.json", ".watch-gate.json"))
    path.write_text(json.dumps(gate), encoding="utf-8")
    return path


def test_a_replaced_video_loses_its_approval(tmp_path):
    # Arrange: an approved render, then someone swaps the file by hand.
    manifest_path, manifest, digest = write_render(tmp_path)
    write_gate(manifest_path, manifest, digest)
    before = library.entry_for(manifest_path, tmp_path)
    (tmp_path / "x.en.mp4").write_bytes(b"a different video")
    # Act
    after = library.entry_for(manifest_path, tmp_path)
    # Assert
    assert before["bytes_verified"] is True
    assert after["bytes_verified"] is False
    assert after["watch"]["publishable"] is False
    assert after["watch"]["state"] == "changed"
    assert after["watch"]["unverified_bytes"] == ["en"]


def test_a_video_with_no_recorded_digest_is_unverified_not_trusted(tmp_path):
    # Arrange: an older manifest that predates digests.
    manifest_path, manifest, _ = write_render(tmp_path)
    stripped = json.loads(manifest_path.read_text(encoding="utf-8"))
    stripped["renditions"][0]["files"][0].pop("sha256")
    manifest_path.write_text(json.dumps(stripped), encoding="utf-8")
    # Act
    entry = library.entry_for(manifest_path, tmp_path)
    # Assert
    assert entry["bytes_verified"] is False
    assert entry["bytes"]["en"]["reason"] == "no recorded digest"


def test_a_gate_from_another_render_cannot_approve_this_one(tmp_path):
    # Arrange: the same app on the same day, a different commit and different bytes.
    manifest_path, manifest, digest = write_render(tmp_path)
    write_gate(manifest_path, manifest, digest, commit="c" * 40, gate_digest="d" * 64)
    # Act
    entry = library.entry_for(manifest_path, tmp_path)
    # Assert
    assert entry["watch"]["publishable"] is False
    assert entry["watch"]["state"] == "mismatched"
    assert any("digest" in problem for problem in entry["identity_problems"])
    assert any("commit" in problem for problem in entry["identity_problems"])


def test_a_gate_that_does_not_name_a_manifest_is_not_an_approval(tmp_path):
    # Arrange: the shape the review called unbound.
    manifest_path, manifest, digest = write_render(tmp_path)
    gate_path = write_gate(manifest_path, manifest, digest)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate.pop("manifest")
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    # Act
    entry = library.entry_for(manifest_path, tmp_path)
    # Assert
    assert entry["watch"]["publishable"] is False
    assert "does not name the manifest" in " ".join(entry["identity_problems"])


def test_a_promotion_for_another_render_is_reported(tmp_path):
    # Arrange
    manifest_path, manifest, digest = write_render(tmp_path)
    write_gate(manifest_path, manifest, digest)
    promotion = {
        "schema": library.PROMOTION_SCHEMA,
        "embed_key": "demos/projects",
        "docs_targets": ["/docs/guides/"],
        "app": "projects",
        "date": "2026-09-17",
        "video_sha256": {"en": "e" * 64},
    }
    (tmp_path / "x.promotion.json").write_text(json.dumps(promotion), encoding="utf-8")
    # Act
    entry = library.entry_for(manifest_path, tmp_path)
    # Assert
    assert any("promotion's en digest" in problem for problem in entry["identity_problems"])


def test_a_manifest_symlinked_out_of_the_root_is_not_indexed(tmp_path):
    # Arrange: a real manifest outside the library, linked in.
    outside = tmp_path / "outside"
    library_dir = tmp_path / "library"
    manifest_path, _, _ = write_render(outside)
    library_dir.mkdir(parents=True, exist_ok=True)
    (library_dir / "x.manifest.json").symlink_to(manifest_path)
    (library_dir / "real.manifest.json").write_text(
        manifest_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    # Act
    index = library.library_index(library_dir)
    # Assert
    assert [entry["manifest"] for entry in index["entries"]] == ["real.manifest.json"]


def test_containment_helpers_refuse_a_symlink_and_an_escape(tmp_path):
    # Arrange
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "link.json").symlink_to(outside)
    (root / "inside.json").write_text("{}", encoding="utf-8")
    # Act / Assert
    assert library.manifest_is_inside(root / "link.json", root.resolve()) is False
    assert library.manifest_is_inside(root / "inside.json", root.resolve()) is True
    assert library.manifest_is_inside(tmp_path / "nothing.json", root.resolve()) is False
