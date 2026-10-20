#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every demo-video selector must still exist in THIS checkout.

A scenario records the real UI. When Hub renames an id or moves a control, the
recording does not fail loudly — it times out mid-flow, or it captures a screen
that no longer matches the narration, and the published video quietly stops being
true. This test is the CI half of scripts/demo_videos/demo_selectors.py: it walks
every scenario against the checkout's templates and scripts, and it fails when a
selector is gone.

The fragile and unverifiable sets are asserted exactly, not as lower bounds:
adding one is a decision, so it has to be written down here with the reasons.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_VIDEOS_DIR = REPO_ROOT / "scripts" / "demo_videos"
SCENARIOS_DIR = DEMO_VIDEOS_DIR / "scenarios"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_scenario import load_scenario  # noqa: E402
from demo_selectors import (  # noqa: E402
    LIVE_CHECKS,
    SELECTOR_CONTRACTS,
    SIGNED_IN_PATHS,
    SourceIndex,
    check_contracts,
    check_scenario,
    fragile_scenario_selectors,
    missing_scenario_selectors,
    unverifiable_scenario_selectors,
)

# Selectors that follow a class or a translated label instead of an id/data
# attribute. They are Monaco's own DOM inside the Writer editor: scitex-writer
# owns that markup, so the fix belongs there (a stable editor id), and the live
# check at record time is what confirms them until it lands.
KNOWN_FRAGILE = {
    ".monaco-editor .view-lines",
    ".monaco-editor textarea",
}
# Selectors whose owner is outside this checkout, so the static sweep cannot see
# them. Same reason as above.
KNOWN_UNVERIFIABLE = KNOWN_FRAGILE

SCENARIO_PATHS = sorted(SCENARIOS_DIR.glob("*.yaml"))


def test_there_is_at_least_one_scenario():
    # Arrange / Act / Assert
    assert SCENARIO_PATHS, "the pipeline ships scenarios; a missing directory is a bug"


@pytest.mark.parametrize("path", SCENARIO_PATHS, ids=lambda item: item.stem)
def test_every_scenario_selector_exists_in_this_checkout(path):
    # Arrange
    scenario = load_scenario(path)
    index = SourceIndex.build(REPO_ROOT)
    # Act
    report = check_scenario(REPO_ROOT, scenario, index)
    # Assert
    assert missing_scenario_selectors(report) == []


@pytest.mark.parametrize("path", SCENARIO_PATHS, ids=lambda item: item.stem)
def test_every_scenario_selector_is_recorded_in_the_contract_map(path):
    # Arrange: a selector a scenario depends on and no contract names is a
    # dependency the stale check cannot report on.
    scenario = load_scenario(path)
    index = SourceIndex.build(REPO_ROOT)
    # Act
    report = check_scenario(REPO_ROOT, scenario, index)
    unregistered = [
        entry["selector"] for entry in report["selectors"]
        if not entry["contract"] and entry["selector"] not in KNOWN_FRAGILE
    ]
    # Assert
    assert unregistered == []


def test_no_scenario_selector_is_fragile_beyond_the_known_writer_list():
    # Arrange
    index = SourceIndex.build(REPO_ROOT)
    # Act
    fragile = {
        selector
        for path in SCENARIO_PATHS
        for selector in fragile_scenario_selectors(check_scenario(REPO_ROOT, load_scenario(path), index))
    }
    # Assert
    assert fragile == KNOWN_FRAGILE


def test_no_selector_is_statically_unverifiable_beyond_the_known_list():
    # Arrange
    index = SourceIndex.build(REPO_ROOT)
    # Act
    unverifiable = {
        selector
        for path in SCENARIO_PATHS
        for selector in unverifiable_scenario_selectors(
            check_scenario(REPO_ROOT, load_scenario(path), index)
        )
    }
    # Assert
    assert unverifiable == KNOWN_UNVERIFIABLE


def test_every_selector_contract_is_satisfied_by_this_checkout():
    # Arrange / Act
    statuses = check_contracts(REPO_ROOT)
    # Assert
    assert [(status.name, status.reason) for status in statuses if not status.ok] == []


def test_the_projects_scenario_is_fully_semantic():
    # Arrange: the Create your first project slice is the one being published, so
    # it gets the strict rule with no exceptions.
    scenario = load_scenario(SCENARIOS_DIR / "projects.yaml")
    index = SourceIndex.build(REPO_ROOT)
    # Act
    report = check_scenario(REPO_ROOT, scenario, index)
    # Assert
    assert [entry["selector"] for entry in report["selectors"] if not entry["semantic"]] == []


def test_live_checks_name_contracts_that_exist():
    # Arrange: a live check on a contract that was renamed away would report a
    # failure against a control the static sweep no longer knows either.
    known = {contract.name for contract in SELECTOR_CONTRACTS}
    # Act
    missing = [
        name for check in LIVE_CHECKS for name in check.contracts if name not in known
    ]
    # Assert
    assert missing == []


def test_live_checks_visit_pages_that_need_no_account():
    # Arrange: the live check runs against a running site with no credentials, so a
    # path with a placeholder or an auth-gated prefix would fail for the wrong
    # reason. The signed-in controls are checked by the render itself.
    # Act
    broken = [
        check.path for check in LIVE_CHECKS
        if not check.path.startswith("/") or "{" in check.path
        or any(check.path.startswith(prefix) for prefix in SIGNED_IN_PATHS)
    ]
    # Assert
    assert broken == []
