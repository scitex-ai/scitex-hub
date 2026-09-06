#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``build_container`` must refuse at the front door when mksquashfs is absent.

WHY THIS TEST EXISTS. Measured 2026-08-26 by scitex-agent-container: BOTH the
prod and staging hub images ship apptainer 1.3.4 and NO mksquashfs, so
``apptainer build`` dies with

    FATAL: while searching for mksquashfs: exec: "mksquashfs": executable file
    not found in $PATH

That failure surfaces DEEP — after the build has started — and the person
reading it is by then debugging apptainer rather than reading a refusal from
hub. The guard moves it to the front door and puts it in our own voice.

WHAT IS DELIBERATELY NOT TESTED: an actual SIF build. Building one needs the
real toolchain and would test apptainer, not this change. The behaviour under
test is THE REFUSAL, which is cheap and exact.

NO MOCKS (STX-NM003). PATH is manipulated with a REAL executable stub in a real
directory, so ``shutil.which`` does its real work against a real filesystem.
The stub is a two-line shell script, not a stand-in object.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from scitex_hub.appmaker import build_container


def _stub(bin_dir: Path, name: str) -> None:
    """Put a REAL executable named ``name`` on disk. Not a mock: shutil.which
    finds it by the same rules it uses in production."""
    p = bin_dir / name
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _app_with_def(app_dir: Path) -> None:
    (app_dir / "manifest.json").write_text(json.dumps({"container": "app.def"}))
    (app_dir / "app.def").write_text("Bootstrap: docker\nFrom: alpine:latest\n")


class TestBuildContainerRefusesWithoutMksquashfs:
    def test_refusal_names_the_binary_the_remedy_and_the_scope(self, tmp_path):
        # Arrange — apptainer PRESENT, mksquashfs ABSENT. That combination is
        # the one the images actually ship, and it is the only one that reaches
        # the new guard: without apptainer the earlier check fires instead.
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        _app_with_def(app_dir)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _stub(bin_dir, "apptainer")

        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(bin_dir)
            # Act
            result = build_container(app_dir)
        finally:
            os.environ["PATH"] = old_path

        # Assert
        assert result["success"] is False, result
        err = result["error"]
        assert "mksquashfs" in err, f"must name the missing binary; got {err!r}"
        assert "squashfs-tools" in err, (
            "must name the REMEDY, not only the absence — a reader who cannot "
            f"act on the message is still stuck; got {err!r}"
        )
        # The scope half. `apptainer exec` does NOT need mksquashfs, and hub's
        # own workspace path only ever execs a prebuilt container — so a reader
        # whose workspaces work must not be left wondering if this is theirs.
        assert "exec" in err and "build" in err, (
            "must distinguish `apptainer build` from `apptainer exec`, or the "
            f"next reader re-derives that analysis from a bare error; got {err!r}"
        )

    def test_control_the_guard_does_not_fire_when_mksquashfs_is_present(
        self, tmp_path
    ):
        # Arrange — POSITIVE CONTROL. With both binaries present the guard must
        # NOT fire, otherwise the test above would pass for a guard that
        # refuses unconditionally, which is the failure mode a one-armed test
        # cannot see.
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        _app_with_def(app_dir)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _stub(bin_dir, "apptainer")
        _stub(bin_dir, "mksquashfs")

        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(bin_dir)
            # Act
            result = build_container(app_dir)
        finally:
            os.environ["PATH"] = old_path

        # Assert — the stub apptainer exits 0, so the call proceeds past the
        # guard. What matters is only that it was NOT refused for mksquashfs.
        assert "mksquashfs not found" not in result.get("error", ""), (
            "the guard fired with mksquashfs present, so it refuses "
            f"unconditionally; got {result!r}"
        )

    def test_a_prebuilt_sif_never_reaches_the_guard(self, tmp_path):
        # Arrange — the exec-vs-build distinction, asserted rather than
        # asserted-in-a-comment. An app shipping a .sif is already built, so it
        # must succeed with NO apptainer and NO mksquashfs anywhere on PATH.
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "manifest.json").write_text(json.dumps({"container": "app.sif"}))
        (app_dir / "app.sif").write_bytes(b"not a real sif, never opened")
        empty_bin = tmp_path / "empty"
        empty_bin.mkdir()

        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(empty_bin)
            # Act
            result = build_container(app_dir)
        finally:
            os.environ["PATH"] = old_path

        # Assert
        assert result["success"] is True, (
            "a prebuilt .sif must not require any build toolchain — this is the "
            f"reason the images have shipped without mksquashfs; got {result!r}"
        )


# EOF
