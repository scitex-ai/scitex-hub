#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the §5 required skills MCP tools (hub_skills_list/get)."""

from __future__ import annotations

import asyncio
import json

import pytest

from scitex_hub._mcp_tools.skills import (
    _list_skill_files,
    _skills_root,
    register_skills_tools,
)


class _CollectingMCP:
    """Minimal FastMCP stand-in: captures @mcp.tool() functions by name."""

    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def _register(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _register


@pytest.fixture
def tools() -> dict:
    mcp = _CollectingMCP()
    register_skills_tools(mcp)
    return mcp.tools


@pytest.fixture
def bundled_skills() -> list:
    return _list_skill_files(_skills_root())


def test_register_exposes_hub_skills_list(tools):
    # Arrange: fixture registered the tools on a collecting stub
    # Act
    registered = set(tools)
    # Assert
    assert "hub_skills_list" in registered


def test_register_exposes_hub_skills_get(tools):
    # Arrange: fixture registered the tools on a collecting stub
    # Act
    registered = set(tools)
    # Assert
    assert "hub_skills_get" in registered


def test_hub_skills_list_counts_bundled_skills(tools, bundled_skills):
    # Arrange: bundled_skills mirrors the CLI `skills list` walk
    # Act
    payload = json.loads(asyncio.run(tools["hub_skills_list"]()))
    # Assert
    assert payload["count"] == len(bundled_skills)


def test_hub_skills_list_names_match_bundle(tools, bundled_skills):
    # Arrange
    expected_names = {p.stem for p in bundled_skills}
    # Act
    payload = json.loads(asyncio.run(tools["hub_skills_list"]()))
    # Assert
    assert {s["name"] for s in payload["skills"]} == expected_names


@pytest.fixture
def first_skill(bundled_skills):
    if not bundled_skills:  # bundle-less checkout — nothing to roundtrip
        pytest.skip("no bundled skills in this checkout")
    return bundled_skills[0]


def test_hub_skills_get_roundtrips_first_skill_content(tools, first_skill):
    # Arrange
    expected_content = first_skill.read_text(encoding="utf-8")
    # Act
    payload = json.loads(asyncio.run(tools["hub_skills_get"](first_skill.stem)))
    # Assert
    assert payload["content"] == expected_content


def test_hub_skills_get_unknown_name_reports_available(tools):
    # Arrange
    missing_name = "no-such-skill-xyz"
    # Act
    payload = json.loads(asyncio.run(tools["hub_skills_get"](missing_name)))
    # Assert
    assert payload["success"] is False and "available" in payload


# EOF
