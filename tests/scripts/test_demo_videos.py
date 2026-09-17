#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: the WebVTT builder, the scenario schema and renditions."""

import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_captions import (  # noqa: E402
    TimedCaption,
    build_transcript,
    build_webvtt,
    wrap_caption,
)
from demo_scenario import (  # noqa: E402
    Scenario,
    ScenarioError,
    load_scenario,
    parse_scenario,
)
from record import language_switch_path, preflight_targets  # noqa: E402

TWO_STEP_VTT = (
    "WEBVTT\n"
    "\n"
    "1\n"
    "00:00:00.000 --> 00:00:02.500\n"
    "Open Create new project\n"
    "\n"
    "2\n"
    "00:00:02.500 --> 00:01:05.250\n"
    "Type a project name\n"
)

MINIMAL_SCENARIO = {
    "app": "demo",
    "title": {"en": "A demo", "ja": "デモ"},
    "languages": {"en": {"locale": "en"}, "ja": {"locale": "ja"}},
    "steps": [
        {"action": "goto", "value": {"en": "/en/", "ja": "/ja/"},
         "narration": {"en": "Go.", "ja": "進みます。"}},
    ],
}


def test_build_webvtt_times_two_steps_as_consecutive_cues():
    # Arrange
    captions = [
        TimedCaption("Open Create new project", 0.0, 2.5),
        TimedCaption("Type a project name", 2.5, 65.25),
    ]
    # Act
    vtt = build_webvtt(captions)
    # Assert
    assert vtt == TWO_STEP_VTT


def test_projects_scenario_yaml_loads_as_a_scenario():
    # Arrange
    path = DEMO_VIDEOS_DIR / "scenarios" / "projects.yaml"
    # Act
    scenario = load_scenario(path)
    # Assert
    assert isinstance(scenario, Scenario) and scenario.steps


def test_projects_scenario_uses_two_synchronized_languages():
    # Arrange
    path = DEMO_VIDEOS_DIR / "scenarios" / "projects.yaml"
    # Act
    scenario = load_scenario(path)
    # Assert
    assert scenario.languages == ["en", "ja"]
    for step in scenario.steps:
        assert set(step.narration) == {"en", "ja"}, f"step {step.action} narrates both languages"
    assert scenario.title == {
        "en": "Create your first project",
        "ja": "はじめてのプロジェクトを作る",
    }


def test_scenario_renditions_are_canonical_per_language():
    # Arrange
    scenario = parse_scenario(MINIMAL_SCENARIO)
    # Act
    renditions = scenario.renditions
    # Assert
    assert [(item.language, item.ui_locale, item.canonical) for item in renditions] == [
        ("en", "en", True),
        ("ja", "ja", True),
    ]
    # The canonical file names never carry a ui- infix: the published catalog
    # paths (and the tests that assert them) must not move.
    assert [item.file_infix for item in renditions] == ["", ""]


def test_scenario_alternate_rendition_records_narration_over_another_ui():
    # Arrange
    raw = dict(MINIMAL_SCENARIO)
    raw["alternates"] = [
        {"language": "ja", "ui_locale": "en", "reason": "The editor is not translated yet."}
    ]
    # Act
    scenario = parse_scenario(raw)
    alternates = [item for item in scenario.renditions if not item.canonical]
    # Assert
    assert [(item.language, item.ui_locale, item.file_infix) for item in alternates] == [
        ("ja", "en", ".ui-en")
    ]
    assert alternates[0].reason == "The editor is not translated yet."


def test_scenario_alternate_needs_a_reason_and_a_different_ui():
    # Arrange
    raw = dict(MINIMAL_SCENARIO)
    raw["alternates"] = [{"language": "ja", "ui_locale": "en"}]
    # Act / Assert
    with pytest.raises(ScenarioError, match="reason is required"):
        parse_scenario(raw)


def test_scenario_alternate_duplicating_the_canonical_ui_is_rejected():
    # Arrange
    raw = dict(MINIMAL_SCENARIO)
    raw["alternates"] = [
        {"language": "ja", "ui_locale": "ja", "reason": "duplicate"}
    ]
    # Act / Assert
    with pytest.raises(ScenarioError, match="already the canonical UI"):
        parse_scenario(raw)


def test_scenario_rejects_an_unknown_top_level_key():
    # Arrange
    raw = dict(MINIMAL_SCENARIO, alternate=[{"language": "ja"}])
    # Act / Assert
    with pytest.raises(ScenarioError, match="unknown keys"):
        parse_scenario(raw)


def test_webvtt_skips_silent_steps_and_transcript_numbers_the_spoken_ones():
    # Arrange
    captions = [
        TimedCaption("", 0.0, 1.0),
        TimedCaption("First spoken line", 1.0, 2.0),
        TimedCaption("Second spoken line", 2.0, 3.0),
    ]
    # Act
    vtt = build_webvtt(captions)
    transcript = build_transcript("A demo", captions)
    # Assert
    assert vtt.count("-->") == 2
    assert "First spoken line" in vtt and "Second spoken line" in vtt
    assert transcript == "A demo\n\n1. First spoken line\n2. Second spoken line\n"


def test_wrap_caption_breaks_japanese_without_spaces():
    # Arrange
    text = "ここはホームです。アプリがここに並んでいます。プロジェクトを作ってみましょう。"
    # Act
    wrapped = wrap_caption(text, 30)
    # Assert
    assert wrapped.count("\n") >= 1
    assert all(len(line) <= 3 * 30 for line in wrapped.split("\n"))


def test_preflight_targets_are_the_goto_pages_with_placeholders_filled():
    # Arrange: a signed-in scenario opens a project path built from the account.
    scenario = parse_scenario({
        "app": "demo",
        "title": {"en": "A demo"},
        "languages": ["en"],
        "steps": [
            {"action": "goto", "value": "/apps/"},
            {"action": "click", "selector": "#create-submit-btn"},
            {"action": "type", "selector": "#name", "value": "x-{run_id}"},
            {"action": "goto", "value": "/{username}/x-{run_id}/"},
            {"action": "goto", "value": "/apps/"},
        ],
    })
    # Act
    targets = preflight_targets(scenario, "demo-user", "PREFLIGHT")
    # Assert
    assert targets == ["/apps/", "/demo-user/x-PREFLIGHT/"]


def test_preflight_targets_of_the_projects_scenario_cover_every_page():
    # Arrange: the render's pages, so the preflight cannot silently check fewer.
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "projects.yaml")
    # Act
    targets = preflight_targets(scenario, "demo-user", "PREFLIGHT")
    # Assert
    assert targets == [
        "/apps/",
        "/new/",
        "/demo-user/sleep-study-PREFLIGHT/",
    ]


def test_language_switch_happens_on_a_page_the_scenario_visits():
    # Arrange: the switch used to run on /apps/ for every scenario, which a
    # signed-out tour cannot reach (it redirects to signup).
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "smoke-public-demos.yaml")
    # Act
    path = language_switch_path(scenario)
    # Assert
    assert path == "/demos/"


def test_language_switch_falls_back_to_the_home_page_without_a_plain_goto():
    # Arrange: every goto carries a placeholder, so no page can be visited first.
    scenario = parse_scenario({
        "app": "demo",
        "title": {"en": "A demo"},
        "languages": ["en"],
        "steps": [{"action": "goto", "value": "/{username}/project/"}],
    })
    # Act / Assert
    assert language_switch_path(scenario) == "/apps/"
