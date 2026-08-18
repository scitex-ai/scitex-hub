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

AND THE GROUPS MUST NOT COLLIDE. The first version of this file asserted only
that the group STRING mentions ``github.workflow`` and ``github.ref``. That is
true of two workflows whose names differ only by case, and GitHub is explicit:

    "The concurrency group name is case insensitive. For example, `prod` and
     `Prod` will be treated as the same concurrency group."
    -- Actions workflow syntax reference, `concurrency`

The repo shipped exactly that pair: the pytest-matrix workflow was
``name: tests`` and ``tests.yml`` was ``name: Tests``, so both resolved to ONE
group and, with cancel-in-progress on a pull request, either could cancel the
other. The cheap victim was the worse one: tests.yml carries
the security regression gates, which are NOT required contexts, so the pull
request would still have merged -- green by absence. A gate that cannot fail is
not a gate, so the uniqueness assertion below is the one that had to exist.
"""

from __future__ import annotations

import re
from collections import defaultdict
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

# A stand-in for github.ref while resolving group keys below. Any single value
# does; what is being compared is whether two DIFFERENT workflows collapse onto
# the same key for the same ref.
SENTINEL_REF = "refs/pull/1/merge"
SENTINEL_REPO = "scitex-ai/scitex-hub"


def _workflow_files() -> list[Path]:
    return sorted(p for p in WORKFLOWS.iterdir() if p.suffix in (".yml", ".yaml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _workflow_name(path: Path) -> str:
    """What ``github.workflow`` evaluates to for this file.

    "The name of the workflow. If the workflow file doesn't specify a `name`,
    the value of this property is the full path of the workflow file in the
    repository." -- github context reference.
    """
    name = _load(path).get("name")
    return name if name else f".github/workflows/{path.name}"


# Every expression this repo is allowed to key a concurrency group on, with the
# value it takes for a given file. Anything else must fail loudly rather than
# be left in the string, where two files would look identical and the
# uniqueness check would pass while measuring nothing.
def _resolve_group(group: str, path: Path) -> str:
    workflow_ref = f"{SENTINEL_REPO}/.github/workflows/{path.name}@{SENTINEL_REF}"
    substitutions = (
        (r"\$\{\{\s*github\.workflow_ref\s*\}\}", workflow_ref),
        (r"\$\{\{\s*github\.workflow\s*\}\}", _workflow_name(path)),
        (r"\$\{\{\s*github\.ref_name\s*\}\}", SENTINEL_REF),
        (r"\$\{\{\s*github\.ref\s*\}\}", SENTINEL_REF),
        (r"\$\{\{\s*github\.head_ref\s*\}\}", SENTINEL_REF),
        (r"\$\{\{\s*github\.event_name\s*\}\}", "pull_request"),
    )
    resolved = group
    for pattern, value in substitutions:
        # Replace via a callable: a plain string replacement would interpret
        # backslash escapes in a workflow name as backreferences.
        resolved = re.sub(pattern, lambda _match, v=value: v, resolved)
    return resolved


def _declared_groups() -> dict[str, str]:
    """``{filename: resolved group key}`` for every file declaring one."""
    groups = {}
    for path in _workflow_files():
        concurrency = _load(path).get("concurrency") or {}
        group = concurrency.get("group")
        if group:
            groups[path.name] = _resolve_group(str(group), path)
    return groups


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


class TestNoTwoWorkflowsShareAConcurrencyGroup:
    """GitHub case-folds group names, so `tests` and `Tests` are one group."""

    def test_the_scan_actually_examined_the_workflow_directory(self):
        # A uniqueness assertion over an empty set passes while measuring
        # nothing -- the exact failure mode this class exists to close. Pin the
        # count the scan really saw, not a separately recomputed one.
        # Arrange
        scanned = _workflow_files()
        # Act
        count = len(scanned)
        # Assert
        assert count >= 10, (
            f"the uniqueness scan found only {count} workflow file(s) under "
            f"{WORKFLOWS}. The repo has fifteen; a scan that sees none would "
            "report every group unique and gate nothing."
        )

    def test_workflow_names_are_unique_when_case_folded(self):
        # Arrange
        by_folded = defaultdict(list)
        for path in _workflow_files():
            by_folded[_workflow_name(path).casefold()].append(path.name)
        # Act
        collisions = {
            folded: files for folded, files in by_folded.items() if len(files) > 1
        }
        # Assert
        assert not collisions, (
            f"workflow names collide when case-folded: {collisions}. GitHub is "
            "explicit that 'the concurrency group name is case insensitive... "
            "`prod` and `Prod` will be treated as the same concurrency group', "
            "so any group keyed on github.workflow puts these files in ONE "
            "group -- and with cancel-in-progress on a pull request they cancel "
            "each other. Two workflows a human cannot tell apart is also a "
            "naming defect on its own: name each for what it gates."
        )

    def test_resolved_group_keys_are_unique_when_case_folded(self):
        # Arrange
        groups = _declared_groups()
        by_folded = defaultdict(list)
        for filename, key in groups.items():
            by_folded[key.casefold()].append(filename)
        # Act
        collisions = {
            folded: files for folded, files in by_folded.items() if len(files) > 1
        }
        # Assert
        assert not collisions, (
            f"these workflows resolve to the SAME concurrency group key for one "
            f"ref: {collisions}. Whichever run starts second cancels the first, "
            "and if the victim carries checks that branch protection does not "
            "require, the pull request still merges -- green by absence."
        )

    @pytest.mark.parametrize("filename", CHECK_WORKFLOWS)
    def test_the_group_key_resolves_completely(self, filename):
        # An expression this test does not know how to resolve would survive
        # verbatim in every file's key, making unrelated workflows look
        # identical -- or, worse, unique when they are not. Fail loudly and
        # teach _resolve_group the new expression instead.
        # Arrange
        concurrency = _load(WORKFLOWS / filename).get("concurrency") or {}
        # Act
        resolved = _resolve_group(str(concurrency.get("group", "")), WORKFLOWS / filename)
        # Assert
        assert "${{" not in resolved, (
            f"{filename} keys its concurrency group on an expression this test "
            f"cannot resolve: {resolved!r}. Add it to _resolve_group with the "
            "value it takes per file, so the uniqueness check above keeps "
            "comparing real keys."
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
