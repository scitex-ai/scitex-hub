#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_workflow_concurrency.py
"""Every check workflow supersedes its own stale runs; publishers never do.

Until 2026-08-15 none of the 15 workflows declared ``concurrency``, so each
push to a pull request launched a complete new suite while the previous
generation kept running and kept holding runner slots. A three-push PR
occupied three generations at once, precisely while it was being iterated --
i.e. exactly when fast feedback matters most.

The rule has two halves and the second is the one that bites if you get it
wrong:

  * PULL REQUEST runs are superseded. Nobody reads a run for a commit that a
    newer commit has replaced.
  * PUSHES to main/develop are NEVER cancelled. Back-to-back merges would
    otherwise kill the earlier merge's run, and anything treating a develop
    run as a gate would lose it silently.

Publishing and mutating workflows are excluded BY NAME with a written reason.
Cancelling a half-finished release or an in-flight merge is worse than the
queue it saves.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# Excluded because cancelling them mid-flight causes real damage. Each entry
# carries its reason and is revisited individually -- never a wildcard, because
# a blanket exemption would also hide every new instance.
PUBLISHING_WORKFLOWS = {
    "pypi-publish-and-github-release-on-tag.yml": (
        "publishes to PyPI and cuts a GitHub release; a cancelled upload is a "
        "broken release"
    ),
    "codeql-pack-publish.yml": "publishes a CodeQL pack; same half-upload hazard",
    "auto-merge-to-develop.yaml": (
        "performs a MERGE; cancelling mid-merge mutates the repository"
    ),
    "cla.yml": (
        "writes the CLA signature file, and its issue_comment trigger has no "
        "meaningful per-ref concurrency group"
    ),
}

EXPECTED_CANCEL = "${{ github.event_name == 'pull_request' }}"


def _workflow_files() -> list[Path]:
    return sorted(p for p in WORKFLOWS.iterdir() if p.suffix in (".yml", ".yaml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


CHECK_WORKFLOWS = [
    p.name for p in _workflow_files() if p.name not in PUBLISHING_WORKFLOWS
]


class TestCheckWorkflowsSupersedeStaleRuns:
    @pytest.mark.parametrize("filename", CHECK_WORKFLOWS)
    def test_the_workflow_declares_a_concurrency_group(self, filename):
        # Arrange
        workflow = _load(WORKFLOWS / filename)
        # Act
        concurrency = workflow.get("concurrency")
        # Assert
        assert concurrency, (
            f"{filename} declares no concurrency group, so every push to a pull "
            "request starts a full new suite while the superseded run keeps "
            "holding runner slots. Add the standard block, or -- if this "
            "workflow publishes, deploys or otherwise mutates state -- add it "
            "to PUBLISHING_WORKFLOWS with the reason."
        )

    @pytest.mark.parametrize("filename", CHECK_WORKFLOWS)
    def test_the_group_is_keyed_per_workflow_and_ref(self, filename):
        # Arrange
        concurrency = _load(WORKFLOWS / filename).get("concurrency") or {}
        # Act
        group = concurrency.get("group", "")
        # Assert
        assert "github.workflow" in group and "github.ref" in group, (
            f"{filename} has concurrency group {group!r}. It must include both "
            "github.workflow and github.ref, or one pull request will cancel "
            "another's runs."
        )

    @pytest.mark.parametrize("filename", CHECK_WORKFLOWS)
    def test_only_pull_request_runs_are_cancelled(self, filename):
        # Arrange
        concurrency = _load(WORKFLOWS / filename).get("concurrency") or {}
        # Act
        cancel = str(concurrency.get("cancel-in-progress", ""))
        # Assert
        assert cancel == EXPECTED_CANCEL, (
            f"{filename} has cancel-in-progress: {cancel!r}, expected "
            f"{EXPECTED_CANCEL!r}. A bare `true` also cancels pushes to "
            "main/develop, so back-to-back merges kill the earlier merge's run "
            "and anyone treating it as a gate loses it silently."
        )


class TestPublishingWorkflowsAreNeverCancelled:
    @pytest.mark.parametrize("filename", sorted(PUBLISHING_WORKFLOWS))
    def test_the_publishing_workflow_does_not_cancel_itself(self, filename):
        # Arrange
        concurrency = _load(WORKFLOWS / filename).get("concurrency") or {}
        # Act
        cancel = str(concurrency.get("cancel-in-progress", "false")).lower()
        # Assert
        assert cancel in ("false", ""), (
            f"{filename} publishes or mutates state and must never be cancelled "
            "mid-flight. Cancelling a half-finished release or an in-flight "
            "merge is worse than the queue it saves."
        )

    @pytest.mark.parametrize("filename", sorted(PUBLISHING_WORKFLOWS))
    def test_the_exclusion_carries_a_written_reason(self, filename):
        # Arrange
        reason = PUBLISHING_WORKFLOWS[filename]
        # Act
        reason_is_substantive = len(reason.split()) >= 5
        # Assert
        assert reason_is_substantive, (
            f"the exclusion for {filename} has no real reason written. An "
            "exemption nobody can review is how a blanket flag gets rebuilt one "
            "entry at a time."
        )


class TestTheExclusionListMatchesReality:
    @pytest.mark.parametrize("filename", sorted(PUBLISHING_WORKFLOWS))
    def test_the_excluded_workflow_still_exists(self, filename):
        # Arrange
        path = WORKFLOWS / filename
        # Act
        exists = path.is_file()
        # Assert
        assert exists, (
            f"PUBLISHING_WORKFLOWS excludes {filename}, which no longer exists. "
            "A stale exemption silently widens as files are renamed -- delete "
            "the entry or point it at the new name."
        )


# EOF
