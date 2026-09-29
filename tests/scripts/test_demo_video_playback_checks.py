#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The playback verifier must fail a state where language and playing file disagree.

The review found the verifier blind to two mismatches a language switch can hide: the
language reported as active not being the language playing, and a caption track left
attached from the rendition we just left. Both are pure functions of the measured
state, so they are pinned here rather than only in a browser run — and these tests
prove the verifier can fail, which is the property that was missing.
"""

import sys
from argparse import Namespace
from pathlib import Path

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from verify_playback import checks_from, name_matches, verdict  # noqa: E402

ARGS = Namespace(tolerance_seconds=0.75, play_seconds=2.0)


def measured(language: str, playing: str, caption: str, *, announced: bool = True) -> dict:
    """A measured switch, as `run_switch` reports it."""
    return {
        "announced": announced,
        "initial": {"language": language, "playingSrc": playing,
                    "expectedSrc": "http://x/ja.mp4", "expectedCaptions": "http://x/ja.vtt",
                    "captionTrackSrc": caption},
        "before": {"position": 10.0, "paused": False, "playbackRate": 1.25},
        "after": {"at": 10.0, "paused": False, "playbackRate": 1.25,
                  "src": "http://x/ja.mp4",
                  "captionsLanguage": "ja", "language": "ja",
                  "playingSrc": "http://x/ja.mp4", "captionTrackSrc": "http://x/ja.vtt"},
        "advanced": {"currentTime": 12.5},
    }


TARGET = {"code": "ja", "src": "ja.mp4", "captions": "ja.vtt", "captionCode": "ja"}


def test_a_consistent_switch_passes_every_check():
    # Arrange
    state = measured("ja", "http://x/ja.mp4", "http://x/ja.vtt")
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert checks["initial_source_matches_language"] is True
    assert checks["initial_captions_match_file"] is True
    assert checks["playing_file_matches_after_switch"] is True
    assert checks["captions_track_matches_file"] is True
    assert verdict(checks) is True


def test_an_active_language_over_another_file_fails():
    # Arrange: the player says Japanese while the English file is playing.
    state = measured("ja", "http://x/en.mp4", "http://x/ja.vtt")
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert checks["initial_source_matches_language"] is False
    assert verdict(checks) is False


def test_a_caption_track_from_the_previous_rendition_fails():
    # Arrange: the JA file is playing but the EN track stayed showing.
    state = measured("ja", "http://x/ja.mp4", "http://x/en.vtt")
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert checks["initial_captions_match_file"] is False
    assert verdict(checks) is False


def test_captions_left_behind_after_the_switch_fail():
    # Arrange: the switch lands the file but keeps the old captions.
    state = measured("ja", "http://x/ja.mp4", "http://x/ja.vtt")
    state["after"]["captionTrackSrc"] = "http://x/en.vtt"
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert checks["captions_track_matches_file"] is False
    assert verdict(checks) is False


def test_a_switch_that_lands_on_the_wrong_file_fails():
    # Arrange: the button was clicked but the English file is still playing.
    state = measured("ja", "http://x/ja.mp4", "http://x/ja.vtt")
    state["after"]["playingSrc"] = "http://x/en.mp4"
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert checks["playing_file_matches_after_switch"] is False
    assert verdict(checks) is False


def test_an_unannounced_switch_passes_nothing():
    # Arrange: the player never announced the switch, so nothing was measured.
    state = measured("ja", "http://x/en.mp4", "http://x/en.vtt", announced=False)
    # Act
    checks = checks_from(state, TARGET, ARGS, 2.0)
    # Assert
    assert verdict(checks) is False
    assert checks["initial_source_matches_language"] is False


def test_name_matching_tolerates_paths_and_queries_but_not_other_files():
    # Arrange / Act / Assert
    assert name_matches("/media/videos/demos/a.en.mp4?x=1", "/media/videos/demos/a.en.mp4")
    assert name_matches("http://host/a.en.mp4", "a.en.mp4")
    assert name_matches("http://host/a.ja.mp4", "a.en.mp4") is False
    assert name_matches("", "a.en.mp4") is False
    assert name_matches("anything", "") is True     # nothing was expected
