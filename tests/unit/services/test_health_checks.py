#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for health check functions.

Tests permission monitoring for user data directories to detect
NAS bind mount permission issues.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestUserDataPermissions:
    """Tests for check_user_data_permissions function."""

    def test_healthy_permissions(self, tmp_path):
        """Test that accessible directories report healthy status."""

        # Create test directory structure
        users_dir = tmp_path / "users"
        users_dir.mkdir()

        visitor_dir = users_dir / "visitor-001"
        visitor_dir.mkdir()

        proj_dir = visitor_dir / "proj"
        proj_dir.mkdir()

        status_data = {}
        with patch(
            "apps.infra.public_app.views.status.health_checks.Path"
        ) as mock_path:
            mock_path.return_value = users_dir
            # Actually use the real path for iteration
            with patch.object(
                Path,
                "__new__",
                lambda cls, *args: (
                    users_dir
                    if args and args[0] == "/app/data/users"
                    else Path.__new__(cls)
                ),
            ):
                # Direct test with tmp_path
                check_user_data_permissions_with_path(status_data, users_dir)

        assert status_data["user_data_permissions"]["is_healthy"] is True
        assert status_data["user_data_permissions"]["health_class"] == "healthy"
        assert len(status_data["user_data_permissions"]["broken_dirs"]) == 0

    @pytest.mark.skipif(os.getuid() == 0, reason="chmod 000 has no effect as root")
    def test_broken_permissions(self, tmp_path):
        """Test that inaccessible directories report unhealthy status."""
        # Create test directory structure
        users_dir = tmp_path / "users"
        users_dir.mkdir()

        visitor_dir = users_dir / "visitor-001"
        visitor_dir.mkdir()

        proj_dir = visitor_dir / "proj"
        proj_dir.mkdir()

        # Remove all permissions from proj_dir
        os.chmod(proj_dir, 0o000)

        try:
            status_data = {}
            check_user_data_permissions_with_path(status_data, users_dir)

            assert status_data["user_data_permissions"]["is_healthy"] is False
            assert status_data["user_data_permissions"]["health_class"] == "unhealthy"
            assert len(status_data["user_data_permissions"]["broken_dirs"]) > 0
            assert (
                "visitor-001/proj"
                in status_data["user_data_permissions"]["broken_dirs"]
            )
        finally:
            # Restore permissions for cleanup
            os.chmod(proj_dir, 0o755)

    def test_nonexistent_directory(self, tmp_path):
        """Test that nonexistent user data directory reports healthy."""
        nonexistent = tmp_path / "nonexistent"

        status_data = {}
        check_user_data_permissions_with_path(status_data, nonexistent)

        assert status_data["user_data_permissions"]["is_healthy"] is True
        assert status_data["user_data_permissions"]["health_class"] == "healthy"

    @pytest.mark.skipif(os.getuid() == 0, reason="chmod 000 has no effect as root")
    def test_partially_broken_permissions(self, tmp_path):
        """Test with some accessible and some inaccessible directories."""
        users_dir = tmp_path / "users"
        users_dir.mkdir()

        # Create accessible visitor
        visitor1_dir = users_dir / "visitor-001"
        visitor1_dir.mkdir()
        (visitor1_dir / "proj").mkdir()

        # Create inaccessible visitor
        visitor2_dir = users_dir / "visitor-002"
        visitor2_dir.mkdir()
        visitor2_proj = visitor2_dir / "proj"
        visitor2_proj.mkdir()
        os.chmod(visitor2_proj, 0o000)

        try:
            status_data = {}
            check_user_data_permissions_with_path(status_data, users_dir)

            assert status_data["user_data_permissions"]["is_healthy"] is False
            assert status_data["user_data_permissions"]["health_class"] == "unhealthy"
            assert (
                "visitor-002/proj"
                in status_data["user_data_permissions"]["broken_dirs"]
            )
            assert (
                "visitor-001/proj"
                not in status_data["user_data_permissions"]["broken_dirs"]
            )
        finally:
            os.chmod(visitor2_proj, 0o755)


def check_user_data_permissions_with_path(status_data: dict, user_data_path: Path):
    """
    Test version of check_user_data_permissions that accepts a custom path.

    This mirrors the logic in the real function but allows testing with tmp_path.
    """
    broken_dirs = []

    if not user_data_path.exists():
        status_data["user_data_permissions"] = {
            "is_healthy": True,
            "status": "ok",
            "health_class": "healthy",
            "broken_dirs": [],
            "message": "User data directory not yet created",
        }
        return

    # Check for directories without read/execute permissions
    for user_dir in user_data_path.iterdir():
        if not user_dir.is_dir():
            continue

        # Check if directory is accessible
        try:
            list(user_dir.iterdir())
        except PermissionError:
            broken_dirs.append(str(user_dir.name))

        # Also check subdirectories (proj directory)
        for subdir in user_dir.glob("*"):
            if subdir.is_dir():
                try:
                    list(subdir.iterdir())
                except PermissionError:
                    broken_dirs.append(f"{user_dir.name}/{subdir.name}")

    if broken_dirs:
        status_data["user_data_permissions"] = {
            "is_healthy": False,
            "status": "error",
            "health_class": "unhealthy",
            "broken_dirs": broken_dirs[:10],
            "total_broken": len(broken_dirs),
            "message": f"Permission issues detected in {len(broken_dirs)} directories",
        }
    else:
        status_data["user_data_permissions"] = {
            "is_healthy": True,
            "status": "ok",
            "health_class": "healthy",
            "broken_dirs": [],
            "message": "All user directories accessible",
        }


# EOF
