#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflows that outsiders can trigger with a write token pin what they run.

``pull_request_target`` and ``issue_comment`` run in this repository's context
with its token, and anyone with a GitHub account can start them on a public
repository. Every action or reusable workflow such a workflow ``uses:`` must
therefore be a full commit SHA, so a later change upstream (a moved branch or
tag) cannot change what runs without a reviewed edit here. Local
(``./``-prefixed) references are part of this repository and exempt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
PRIVILEGED_EVENTS = {"pull_request_target", "issue_comment", "workflow_run"}
FULL_SHA = re.compile(r"@[0-9a-f]{40}$")


def _triggers(doc: dict) -> set[str]:
    # PyYAML reads the bare key `on` as boolean True.
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on or {})


def _uses(doc: dict) -> list[str]:
    refs = []
    for job in (doc.get("jobs") or {}).values():
        if "uses" in job:
            refs.append(job["uses"])
        for step in job.get("steps") or []:
            if "uses" in step:
                refs.append(step["uses"])
    return refs


def _privileged_refs() -> list[tuple[str, str]]:
    found = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        doc = yaml.safe_load(path.read_text()) or {}
        if _triggers(doc) & PRIVILEGED_EVENTS:
            found.extend(
                (path.name, ref) for ref in _uses(doc) if not ref.startswith("./")
            )
    return found


def test_privileged_workflows_exist_to_check():
    # Arrange
    refs = _privileged_refs()
    # Act
    names = {name for name, _ in refs}
    # Assert
    assert "cla.yml" in names


@pytest.mark.parametrize("workflow,ref", _privileged_refs())
def test_privileged_workflow_reference_is_a_full_commit_sha(workflow, ref):
    # Arrange
    pattern = FULL_SHA
    # Act
    pinned = bool(pattern.search(ref))
    # Assert
    assert pinned, f"{workflow}: {ref} must be pinned to a full commit SHA"
