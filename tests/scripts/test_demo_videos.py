#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: the WebVTT builder and the scenario YAML schema."""

import sys
from pathlib import Path

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_captions import TimedCaption, build_webvtt  # noqa: E402
from demo_scenario import Scenario, load_scenario  # noqa: E402

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
