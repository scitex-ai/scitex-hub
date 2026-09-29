#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reviewed library blockers: a malformed manifest, a live docs link, schemeless.

Three of the seven findings on PR 937 were rules about what the library accepts, and
each one is a rule this module can be asked directly. They are pinned here so the
review's own reproductions become regressions: a manifest that declares our schema and
the wrong shapes must read as unreadable instead of raising on a staff page, a promoted
asset must not be able to inject ``javascript:`` into a link we render, and the readers
must survive a manifest they were handed by hand.
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


def a_manifest(**overrides):
    manifest = {
        "schema": library.MANIFEST_SCHEMA,
        "app": "projects",
        "date": "2026-09-17",
        "commit": "a" * 40,
        "renditions": [
            {
                "language": "en",
                "viewport": "desktop",
                "canonical": True,
                "files": [{"role": "video", "name": "x.en.mp4"}],
            }
        ],
    }
    manifest.update(overrides)
    return manifest


def test_a_well_formed_manifest_has_no_problems():
    # Arrange / Act / Assert
    assert library.manifest_problems(a_manifest()) == []


def test_a_manifest_with_the_right_schema_and_wrong_shapes_is_unreadable():
    # Arrange: the review's malformed case — the schema string was right.
    cases = [
        a_manifest(renditions="projects-2026-09-17.en.mp4"),
        a_manifest(renditions=[]),
        a_manifest(renditions=[{"language": "en", "files": "x.en.mp4"}]),
        a_manifest(renditions=[{"language": "en", "files": [["video"]]}]),
        a_manifest(renditions=[{"language": 1, "files": []}]),
        a_manifest(app={}, date=[]),
    ]
    # Act / Assert
    for manifest in cases:
        assert library.manifest_problems(manifest), manifest


def test_read_manifest_refuses_a_malformed_file_instead_of_raising(tmp_path):
    # Arrange: on disk, so the whole read path is exercised.
    path = tmp_path / "x.manifest.json"
    path.write_text(json.dumps(a_manifest(renditions=[{"files": [[1]]}])), encoding="utf-8")
    # Act
    manifest = library.read_manifest(path)
    # Assert
    assert manifest == {}


def test_the_readers_survive_a_manifest_handed_to_them_by_hand():
    # Arrange: a caller may pass a raw dict; nothing may raise while formatting it.
    hostile = {"renditions": "not a list", "files": [[1]], "language": 1}
    # Act / Assert
    assert library.rendition_rows(hostile) in ([], None) or isinstance(
        library.rendition_rows(hostile), list
    )


def test_a_watch_gate_that_is_not_the_shape_we_expect_does_not_raise():
    # Arrange
    gate = {"schema": library.WATCH_GATE_SCHEMA, "required_languages": "en",
            "watches": "none", "artifacts": [1, 2]}
    # Act
    state = library.watch_state(gate)
    # Assert
    assert state["state"] in ("no-gate", "unwatched", "partial", "watched", "stale", "failed")
    assert state["publishable"] is False


def test_docs_targets_accept_guides_and_refuse_a_live_scheme():
    # Arrange / Act / Assert
    assert library.safe_docs_target("/docs/guides/demos/") == "/docs/guides/demos/"
    assert library.safe_docs_target("https://docs.scitex.ai/x") == "https://docs.scitex.ai/x"
    for hostile in ("javascript:alert(1)", "JavaScript:alert(1)", "data:text/html,x",
                    "//evil.example/x", "vbscript:x", "", "  ", None, 42,
                    "/docs/\njavascript:x"):
        assert library.safe_docs_target(hostile) == "", hostile
