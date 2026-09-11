#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression gates for the product-screenshot route partition."""

from pathlib import Path

import pytest
import yaml

from tests.e2e.playwright.test_capture_screenshots import ALL_PAGES, pages_for_shard

WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "screenshots.yml"


def _capture_script():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["screenshots"]["steps"]
    return next(
        step["run"] for step in steps if step.get("name") == "Capture screenshots"
    )


def test_two_shards_cover_every_page_exactly_once():
    shards = [pages_for_shard(ALL_PAGES, index, 2) for index in range(2)]
    flattened = [page for shard in shards for page in shard]

    assert len(flattened) == len(set(flattened)) == len(ALL_PAGES)


def test_two_shards_are_balanced_to_one_page():
    sizes = [len(pages_for_shard(ALL_PAGES, index, 2)) for index in range(2)]

    assert max(sizes) - min(sizes) <= 1


def test_workflow_launches_both_route_shards():
    script = _capture_script()

    assert {"capture_shard 0 &", "capture_shard 1 &"}.issubset(set(script.splitlines()))


def test_workflow_declares_the_same_shard_count_as_the_partition_gate():
    script = _capture_script()

    assert "SCITEX_SCREENSHOT_SHARD_COUNT=2" in script


def test_workflow_merges_both_reports_into_the_canonical_report():
    script = _capture_script()

    assert "for shard_index in 0 1; do" in script


@pytest.mark.parametrize("index,count", [(-1, 2), (2, 2), (0, 0)])
def test_invalid_shard_coordinates_are_rejected(index, count):
    with pytest.raises(ValueError):
        pages_for_shard(ALL_PAGES, index, count)
