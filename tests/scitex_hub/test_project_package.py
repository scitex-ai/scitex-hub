#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/test_project_package.py

"""Tests that ``scitex_hub.project`` is a package exposing CRUD plus the
sandboxed MCP file-operation handlers.

The umbrella ``scitex.project`` (and its ``_mcp.handlers``) re-export from here,
so these import paths must remain stable.
"""

import asyncio

import pytest


@pytest.fixture
def data_root(tmp_path):
    """Point the handlers' sandbox root at a tmp dir; restore on teardown."""
    from scitex_hub.project._mcp import handlers

    original = handlers.ALLOWED_DATA_ROOT
    handlers.ALLOWED_DATA_ROOT = str(tmp_path)
    try:
        yield tmp_path
    finally:
        handlers.ALLOWED_DATA_ROOT = original


def test_project_crud_importable():
    # Arrange
    # Act
    from scitex_hub.project import (
        project_create,
        project_delete,
        project_list,
        project_rename,
    )

    # Assert
    assert all(
        callable(fn)
        for fn in (project_list, project_create, project_delete, project_rename)
    )


def test_mcp_handlers_importable():
    # Arrange
    # Act
    from scitex_hub.project._mcp.handlers import (
        exec_python_handler,
        exec_shell_handler,
        list_files_handler,
        read_file_handler,
        search_files_handler,
        write_file_handler,
    )

    # Assert
    assert all(
        callable(fn)
        for fn in (
            list_files_handler,
            read_file_handler,
            write_file_handler,
            search_files_handler,
            exec_python_handler,
            exec_shell_handler,
        )
    )


def test_write_then_read_roundtrip(data_root):
    # Arrange
    from scitex_hub.project._mcp import handlers

    project_dir = data_root / "alice" / "proj"
    project_dir.mkdir(parents=True)
    # Act
    write_result = asyncio.run(
        handlers.write_file_handler(str(project_dir), "notes.txt", "hello")
    )
    # Assert
    assert write_result["success"] is True


def test_read_returns_written_content(data_root):
    # Arrange
    from scitex_hub.project._mcp import handlers

    project_dir = data_root / "bob" / "proj"
    project_dir.mkdir(parents=True)
    asyncio.run(handlers.write_file_handler(str(project_dir), "notes.txt", "hello"))
    # Act
    read_result = asyncio.run(handlers.read_file_handler(str(project_dir), "notes.txt"))
    # Assert
    assert read_result["content"] == "hello"


def test_path_traversal_is_blocked(data_root):
    # Arrange
    from scitex_hub.project._mcp import handlers

    project_dir = data_root / "carol" / "proj"
    project_dir.mkdir(parents=True)
    # Act
    result = asyncio.run(
        handlers.read_file_handler(str(project_dir), "../../../../etc/passwd")
    )
    # Assert
    assert result["success"] is False


# EOF
