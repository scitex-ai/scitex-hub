#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: the WebVTT builder, the scenario schema and renditions."""

import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_captions import (  # noqa: E402
    Chapter,
    TimedCaption,
    build_chapter_vtt,
    build_transcript,
    build_webvtt,
    chapter_timestamp,
    wrap_caption,
)
from demo_scenario import (  # noqa: E402
    Scenario,
    ScenarioError,
    load_scenario,
    parse_scenario,
)
from record import (  # noqa: E402
    artifact_role,
    empty_selection_message,
    language_switch_path,
    preflight_target_kinds,
    preflight_targets,
)

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


def test_preflight_knows_which_page_its_own_run_creates():
    # Arrange: `/demo-user/sleep-study-PREFLIGHT/` cannot exist before the render
    # that creates it; requiring it to answer 200 failed a render that worked.
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "projects.yaml")
    # Act
    kinds = preflight_target_kinds(scenario, "demo-user", "PREFLIGHT")
    # Assert
    assert [(entry["path"], entry["creates"]) for entry in kinds] == [
        ("/apps/", False),
        ("/new/", False),
        ("/demo-user/sleep-study-PREFLIGHT/", True),
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


def test_chapters_of_the_projects_scenario_narrate_the_whole_walkthrough():
    # Arrange: the chapter map is what keeps an alternate rendition navigable, so
    # every step that narrates one is named in both languages.
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "projects.yaml")
    # Act / Assert
    assert [step.chapter for step in scenario.steps if step.narration] == [
        {"en": "Home", "ja": "ホーム"},
        {"en": "Create a project", "ja": "プロジェクトを作る"},
        {"en": "Name", "ja": "名前"},
        {"en": "Description", "ja": "説明"},
        {"en": "Create", "ja": "作成"},
        {"en": "Open a file", "ja": "ファイルを開く"},
        {"en": "Your project", "ja": "あなたのプロジェクト"},
    ]


def test_a_scenario_may_leave_the_chapters_out():
    # Arrange: chapters are optional; a scenario without them still records.
    scenario = parse_scenario(MINIMAL_SCENARIO)
    # Act / Assert
    assert all(step.chapter == {} for step in scenario.steps)


def test_build_chapter_vtt_names_each_span():
    # Arrange
    chapters = [
        Chapter("Home", 0.0, 4.5),
        Chapter("Create a project", 4.5, 12.25),
    ]
    # Act
    vtt = build_chapter_vtt(chapters)
    # Assert
    assert vtt == (
        "WEBVTT\n"
        "\n"
        "1\n"
        "00:00:00.000 --> 00:00:04.500\n"
        "Home\n"
        "\n"
        "2\n"
        "00:00:04.500 --> 00:00:12.250\n"
        "Create a project\n"
    )


def test_transcript_carries_a_youtube_style_chapter_list():
    # Arrange: YouTube reads chapters from the description as MM:SS lines.
    captions = [TimedCaption("First spoken line", 0.0, 4.5),
                TimedCaption("Second spoken line", 4.5, 12.25)]
    chapters = [Chapter("Home", 0.0, 4.5), Chapter("Create a project", 65.0, 70.0)]
    # Act
    transcript = build_transcript("A demo", captions, chapters)
    # Assert
    assert transcript == (
        "A demo\n"
        "\n"
        "Chapters\n"
        "00:00 Home\n"
        "01:05 Create a project\n"
        "\n"
        "1. First spoken line\n"
        "2. Second spoken line\n"
    )


def test_transcript_without_chapters_is_unchanged():
    # Arrange
    captions = [TimedCaption("Only line", 0.0, 1.0)]
    # Act / Assert
    assert build_transcript("A demo", captions) == "A demo\n\n1. Only line\n"


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "00:00"), (59.9, "00:59"), (60, "01:00"), (3599, "59:59"), (3600, "1:00:00")],
)
def test_chapter_timestamp_matches_the_form_youtube_accepts(seconds, expected):
    # Arrange / Act / Assert
    assert chapter_timestamp(seconds) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("demo-2026-09-17.en.mp4", "video"),
        ("demo-2026-09-17.en.webm", "raw"),
        ("demo-2026-09-17.en.vtt", "captions"),
        ("demo-2026-09-17.en.chapters.vtt", "chapters"),
        ("demo-2026-09-17.en.txt", "transcript"),
        ("demo-2026-09-17.en.thumbnail.png", "thumbnail"),
    ],
)
def test_artifact_role_is_not_fooled_by_the_chapter_file(name, expected):
    # Arrange / Act / Assert: both caption and chapter tracks end in .vtt, and a
    # manifest that confuses them reports the wrong artifact for the watch gate.
    assert artifact_role(Path(name)) == expected


def test_an_empty_selection_is_refused_with_what_the_scenario_offers():
    # Arrange: `--viewports mobile` against a desktop-only scenario recorded
    # nothing and exited 0, leaving a manifest with an empty matrix.
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "writer.yaml")
    # Act
    message = empty_selection_message([], ["en", "ja"], ["en:en", "ja:ja"], scenario)
    # Assert
    assert "nothing to record" in message
    assert "viewports=none" in message
    assert "desktop" in message
    assert "mobile" not in message.split("the scenario offers")[1]


def test_the_smoke_scenario_declares_both_viewports():
    # Arrange: the only scenario that can be rendered without an account is also
    # the one that has to exercise the 390 px path.
    scenario = load_scenario(DEMO_VIDEOS_DIR / "scenarios" / "smoke-public-demos.yaml")
    # Act / Assert
    assert scenario.viewports == ["desktop", "mobile"]
