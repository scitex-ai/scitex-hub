#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adversarial regressions for the reviewed pipeline defects.

Each test is a way something got through before the independent review: a scenario
that leaves the site, names that write outside the render root, and a redirect that
takes the recording off-origin after the fact. The refusals are asserted to be
refusals — a traceback from deep inside Playwright is not a fix.
"""

import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_scenario import ACTIONS, ScenarioError, parse_scenario, parse_step  # noqa: E402
from record import (  # noqa: E402
    assert_same_origin,
    output_name_problems,
    safe_site_path,
)

MINIMAL = {
    "app": "demo",
    "title": {"en": "A demo"},
    "languages": ["en"],
    "steps": [{"action": "goto", "value": "/apps/"}],
}


def scenario_with_goto(value: str) -> dict:
    raw = dict(MINIMAL)
    raw["steps"] = [{"action": "goto", "value": value}]
    return raw


@pytest.mark.parametrize(
    "value",
    ["https://example.com/", "http://127.0.0.1:8000/x", "//evil.example/x",
     "javascript:alert(1)", "apps/", ""],
)
def test_a_goto_that_leaves_the_site_is_refused_at_load(value):
    # Arrange / Act / Assert: refused before a browser exists, so no code path can
    # navigate first — the language switch used to run before the step guard.
    with pytest.raises(ScenarioError, match="site path|needs a value"):
        parse_scenario(scenario_with_goto(value))


@pytest.mark.parametrize("value", ["/apps/", "/demos/watch/guide-create-first-project/",
                                   "/{username}/sleep-study-{run_id}/"])
def test_a_site_path_is_accepted(value):
    # Arrange / Act
    scenario = parse_scenario(scenario_with_goto(value))
    # Assert
    assert scenario.steps[0].value["en"] == value


@pytest.mark.parametrize(
    "value,expected",
    [("/apps/", True), ("/{username}/x/", True), ("//evil/x", False),
     ("https://evil/x", False), ("apps/", False), ("", False), ("/a\\b", False)],
)
def test_safe_site_path_is_the_runtime_half_of_the_same_rule(value, expected):
    # Arrange / Act / Assert
    assert safe_site_path(value) is expected


@pytest.mark.parametrize(
    "app,date,problems",
    [
        ("../../etc", "2026-09-17", 1),
        ("projects", "../../escaped", 1),
        ("Projects", "2026-09-17", 1),
        ("projects", "2026-9-17", 1),
        ("projects", "2026-09-17", 0),
        ("demo-app", "2026-09-17", 0),
    ],
)
def test_names_that_become_files_are_constrained(app, date, problems):
    # Arrange / Act
    found = output_name_problems(app, date)
    # Assert
    assert len(found) == problems, found


class _StubPage:
    def __init__(self, url):
        self.url = url


def test_a_redirect_off_origin_is_caught_after_the_fact():
    # Arrange: the value in the scenario was a site path; the site redirected away.
    page = _StubPage("https://evil.example/landing/")
    # Act / Assert
    with pytest.raises(RuntimeError, match="left the recording origin"):
        assert_same_origin(page, "http://127.0.0.1:8000")


def test_staying_on_origin_is_accepted():
    # Arrange
    page = _StubPage("http://127.0.0.1:8000/apps/")
    # Act / Assert
    assert_same_origin(page, "http://127.0.0.1:8000") is None


def test_a_port_difference_is_a_different_origin():
    # Arrange: same host, different port — still not the recording origin.
    page = _StubPage("http://127.0.0.1:9000/apps/")
    # Act / Assert
    with pytest.raises(RuntimeError, match="left the recording origin"):
        assert_same_origin(page, "http://127.0.0.1:8000")


def test_assert_selector_is_a_real_action_and_requires_its_selector():
    # Arrange: a scenario that asserts the app shell opened for this project.
    step = {"action": "assert_selector",
            "selector": '#app-mount[data-app-slug="figrecipe"]',
            "narration": {"en": "The figure editor", "ja": "図のエディタ"}}
    # Act
    parsed = parse_step(step, 1, ("en", "ja"))
    # Assert: it is a first-class action, checked like any other, not a bare click.
    assert parsed.action == "assert_selector"
    assert parsed.action in ACTIONS
    with pytest.raises(ScenarioError):
        parse_step({"action": "assert_selector", "narration": step["narration"]}, 2, ("en", "ja"))


def test_an_unknown_action_is_still_refused():
    # Arrange / Act / Assert: adding one action must not open the door to any action.
    with pytest.raises(ScenarioError):
        parse_step({"action": "assert_http_500", "selector": "#x",
                    "narration": {"en": "x", "ja": "x"}}, 1, ("en", "ja"))
