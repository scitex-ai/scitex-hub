#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: reproducible metadata for a render."""

import json
import sys
from pathlib import Path

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_manifest import (  # noqa: E402
    MANIFEST_SCHEMA,
    build_manifest,
    file_digest,
    find_manifest,
    git_state,
    load_manifest,
    manifest_path,
    manifest_report,
    summarize,
    text_digest,
    verify_manifest,
    write_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

SCENARIO_TEXT = """app: demo
title:
  en: A demo
  ja: デモ
languages: [en, ja]
steps:
  - action: goto
    value: /apps/
    narration: {en: Go., ja: 進みます。}
"""

TOOLS_INFO = {
    "python": "3.12.0",
    "playwright": "1.55.0",
    "narration_backend": "gtts",
    "voice": True,
    "caption_font": "Noto Sans JP",
}


def write_scenario(root: Path) -> Path:
    path = root / "scenarios" / "demo.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SCENARIO_TEXT, encoding="utf-8")
    return path


def write_artifacts(out_dir: Path, language: str) -> list[dict]:
    """Real files on disk, digested the way the recorder digests them."""
    records = []
    for role, suffix, body in (
        ("video", "mp4", b"fake-mp4-bytes"),
        ("captions", "vtt", b"WEBVTT\n"),
        ("transcript", "txt", b"A demo\n"),
    ):
        path = out_dir / f"demo-2026-09-17.{language}.{suffix}"
        path.write_bytes(body)
        record = dict(file_digest(path))
        record["role"] = role
        records.append(record)
    return records


def build(out_dir: Path, tmp_path: Path, languages=("en", "ja")) -> dict:
    scenario = write_scenario(tmp_path)
    renditions = [
        {
            "language": language,
            "ui_locale": language,
            "canonical": True,
            "viewport": "desktop",
            "duration_seconds": 21.5,
            "narration_seconds": 18.0,
            "cues": 1,
            "files": write_artifacts(out_dir, language),
        }
        for language in languages
    ]
    return build_manifest(
        app="demo",
        date="2026-09-17",
        titles={"en": "A demo", "ja": "デモ"},
        scenario_path=scenario,
        repo_root=REPO_ROOT,
        base_url="http://127.0.0.1:8000",
        renditions=renditions,
        tools_info=TOOLS_INFO,
        contracts={"fingerprint": "f" * 64, "schema": "scitex.demo-video.ui-contract/1"},
        viewports=["desktop"],
        languages=list(languages),
    )


def test_manifest_records_the_scenario_digest_and_the_source_commit(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Act
    manifest = build(out_dir, tmp_path)
    # Assert
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["scenario"]["sha256"] == text_digest(SCENARIO_TEXT)
    assert len(manifest["source"]["commit"]) == 40
    assert manifest["source"]["branch"]
    assert manifest["environment"]["narration_backend"] == "gtts"
    assert manifest["ui_contract"]["fingerprint"] == "f" * 64


def test_manifest_round_trips_through_the_written_file(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest = build(out_dir, tmp_path)
    path = write_manifest(manifest_path(out_dir, "demo", "2026-09-17"), manifest)
    # Act
    loaded = load_manifest(path)
    # Assert
    assert path.name == "demo-2026-09-17.manifest.json"
    assert loaded == manifest
    assert find_manifest(out_dir, "demo") == path
    assert find_manifest(out_dir, "demo", "2026-09-17") == path
    assert find_manifest(out_dir, "other") is None


def test_manifest_verification_accepts_the_files_it_recorded(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest = build(out_dir, tmp_path)
    # Act
    verdict = verify_manifest(manifest, out_dir)
    # Assert
    assert verdict["checked"] == 6
    assert verdict["mismatches"] == []
    assert verdict["verified"] is True


def test_a_replaced_artifact_fails_manifest_verification(tmp_path):
    # Arrange: someone re-encoded one published file by hand.
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest = build(out_dir, tmp_path)
    (out_dir / "demo-2026-09-17.ja.mp4").write_bytes(b"a different encode")
    # Act
    verdict = verify_manifest(manifest, out_dir)
    # Assert
    assert verdict["verified"] is False
    assert verdict["mismatches"] == [
        {
            "name": "demo-2026-09-17.ja.mp4",
            "reason": "digest differs from the manifest",
            "manifest_bytes": len(b"fake-mp4-bytes"),
            "disk_bytes": len(b"a different encode"),
        }
    ]


def test_a_deleted_artifact_fails_manifest_verification(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest = build(out_dir, tmp_path)
    (out_dir / "demo-2026-09-17.en.vtt").unlink()
    # Act
    verdict = verify_manifest(manifest, out_dir)
    # Assert
    assert verdict["mismatches"] == [
        {"name": "demo-2026-09-17.en.vtt", "reason": "file is gone"}
    ]


def test_manifest_watch_gate_lists_every_language_as_required(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Act
    manifest = build(out_dir, tmp_path)
    # Assert
    assert manifest["watch_gate"]["required_languages"] == ["en", "ja"]
    assert manifest["watch_gate"]["status"] == "pending"


def test_summarize_shows_the_matrix_without_the_file_digests(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest = build(out_dir, tmp_path)
    # Act
    summary = summarize(manifest)
    # Assert
    assert summary["app"] == "demo"
    assert [item["language"] for item in summary["renditions"]] == ["en", "ja"]
    assert "sha256" not in json.dumps(summary)


def test_git_state_reports_a_real_commit_for_this_checkout():
    # Arrange / Act
    state = git_state(REPO_ROOT)
    # Assert
    assert len(state["commit"]) == 40
    assert isinstance(state["dirty"], bool)
    assert state["dirty_file_count"] >= 0


def write_contract_owners(root: Path) -> None:
    """A checkout whose files carry every contract token, so nothing is stale."""
    from demo_selectors import SELECTOR_CONTRACTS

    by_owner: dict[str, list[str]] = {}
    for contract in SELECTOR_CONTRACTS:
        by_owner.setdefault(contract.owner, []).append(contract.token)
    for owner, tokens in by_owner.items():
        path = root / owner
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(tokens), encoding="utf-8")


def test_manifest_report_marks_a_published_render_intact_and_current(tmp_path):
    # Arrange: a render made from this checkout's contract set, files present.
    from demo_selectors import SELECTOR_CONTRACTS, contract_fingerprint

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    write_contract_owners(repo)
    manifest = build(out_dir, tmp_path)
    manifest["ui_contract"]["fingerprint"] = contract_fingerprint()
    manifest["ui_contract"]["contracts"] = {
        contract.name: contract.version for contract in SELECTOR_CONTRACTS
    }
    write_manifest(manifest_path(out_dir, "demo", "2026-09-17"), manifest)
    # Act
    rows = manifest_report(out_dir, repo)
    # Assert
    assert len(rows) == 1
    assert rows[0]["manifest"] == "demo-2026-09-17.manifest.json"
    assert rows[0]["artifacts_verified"] is True
    assert rows[0]["stale"] is False
    assert rows[0]["changed_contracts"] == []
    assert rows[0]["watch_gate"] == "pending"


def test_manifest_report_marks_a_render_stale_after_a_contract_moves(tmp_path):
    # Arrange: the same render, but the checkout's contracts are not the recorded ones.
    from demo_selectors import contract_fingerprint

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    write_contract_owners(repo)
    manifest = build(out_dir, tmp_path)
    manifest["ui_contract"]["fingerprint"] = "0" * 64  # recorded from another release
    manifest["ui_contract"]["contracts"] = {}
    write_manifest(manifest_path(out_dir, "demo", "2026-09-17"), manifest)
    # Act
    rows = manifest_report(out_dir, repo)
    # Assert
    assert contract_fingerprint() != "0" * 64
    assert rows[0]["stale"] is True
    assert rows[0]["artifacts_verified"] is True  # the files are fine; the UI moved


def test_manifest_report_flags_a_replaced_file(tmp_path):
    # Arrange
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    write_contract_owners(repo)
    manifest = build(out_dir, tmp_path)
    write_manifest(manifest_path(out_dir, "demo", "2026-09-17"), manifest)
    (out_dir / "demo-2026-09-17.en.mp4").write_bytes(b"hand-made")
    # Act
    rows = manifest_report(out_dir, repo)
    # Assert
    assert rows[0]["artifacts_verified"] is False
    assert rows[0]["artifact_mismatches"][0]["name"] == "demo-2026-09-17.en.mp4"


def test_manifest_report_on_a_directory_of_older_videos_is_empty_not_a_guess(tmp_path):
    # Arrange: the 2026-09-14 guides predate the manifest; there is nothing to read.
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "projects-2026-09-14.en.mp4").write_bytes(b"published before manifests")
    # Act
    rows = manifest_report(out_dir, tmp_path)
    # Assert
    assert rows == []
