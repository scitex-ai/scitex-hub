#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security tests for filesystem-utils write containment."""

from apps.infra.project_app.services.filesystem_utils.file_operations import (
    write_file_content,
)


def test_write_rejects_path_outside_trusted_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "secret.txt"

    result = write_file_content(outside, "pwned", trusted_root=root)

    assert result == (False, "Invalid file path")


def test_write_rejects_symlink_escape(tmp_path):
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)

    result = write_file_content(
        root / "link" / "secret.txt", "pwned", trusted_root=root
    )

    assert result == (False, "Invalid file path")


def test_write_accepts_path_inside_trusted_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    target = root / "notes" / "safe.txt"

    result = write_file_content(target, "safe", trusted_root=root)

    assert result[0] is True
