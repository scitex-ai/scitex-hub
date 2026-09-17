#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Narration backend/voice selection and the theme option.

The public demos policy is English only, light mode, one chosen voice — so both the
provider and the theme stop being implicit. These tests pin the rules that decide
which voice a backend gets, that a missing voice fails before a render rather than
during one, and that the theme is applied through the site's own preference key and
then verified instead of assumed.
"""

import json
import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_manifest import toolchain  # noqa: E402
from demo_narration import (  # noqa: E402
    NARRATION_BACKENDS,
    NarrationUnavailable,
    voice_for,
)
from record import (  # noqa: E402
    first_visual_step,
    theme_from_background,
    theme_init_script,
)


def test_gtts_is_per_language_so_its_voice_defaults_to_the_language():
    # Arrange / Act / Assert
    assert voice_for("gtts", "", "ja") == "ja"
    assert voice_for("gtts", "", "en") == "en"
    assert voice_for("gtts", "en", "ja") == "en"  # an explicit voice still wins


def test_elevenlabs_requires_a_named_voice_and_says_why():
    # Arrange: a speaker is not a language; passing "en" would pick the wrong voice.
    with pytest.raises(NarrationUnavailable, match="needs a voice name or id"):
        voice_for("elevenlabs", "", "en")
    # Act / Assert
    assert voice_for("elevenlabs", "sarah", "en") == "sarah"
    assert voice_for("elevenlabs", "EXAVITQu4vr4xnSDxMaL", "ja") == "EXAVITQu4vr4xnSDxMaL"


def test_the_supported_backends_are_declared():
    # Arrange / Act / Assert: the CLI choices come from this list.
    assert set(NARRATION_BACKENDS) == {"gtts", "elevenlabs"}


def test_the_manifest_records_the_voice_a_render_used():
    # Arrange: a rollout that changes voice changes the video, so it is evidence.
    # Act
    info = toolchain(narration_backend="elevenlabs", narration_voice="sarah", voice=True)
    # Assert
    assert info["narration_backend"] == "elevenlabs"
    assert info["narration_voice"] == "sarah"
    assert info["voice"] is True


def test_the_theme_script_uses_the_site_s_own_preference_keys():
    # Arrange: the keys static/shared/ts/utils/theme-switcher.ts writes.
    # Act
    script = theme_init_script("light")
    # Assert
    assert 'localStorage.setItem(\'stx-theme\', "light")' in script
    assert 'localStorage.setItem(\'scitex-theme-preference\', "light")' in script
    assert 'setAttribute(\'data-theme\', "light")' in script


def test_the_theme_script_quotes_its_argument_so_it_cannot_break_out():
    # Arrange / Act: a value with a quote and a newline must stay a JS string.
    value = "light'; alert(1); //\nmore"
    script = theme_init_script(value)
    # Assert: the value appears exactly as json.dumps writes it, so the injected
    # expression is inert text inside a literal rather than code, and the newline
    # is escaped instead of breaking the statement across lines.
    assert json.dumps(value) in script
    assert "\nmore" not in script  # no raw newline


def test_the_theme_check_lands_on_the_first_step_that_shows_a_page():
    # Arrange: the theme is verified once something is on screen, not after the last step.
    from demo_scenario import parse_scenario

    scenario = parse_scenario({
        "app": "demo",
        "title": {"en": "A demo"},
        "languages": ["en"],
        "steps": [
            {"action": "goto", "value": "/demos/"},
            {"action": "click", "selector": "#x"},
            {"action": "goto", "value": "/y/"},
        ],
    })
    # Act / Assert
    assert first_visual_step(scenario) == 0


@pytest.mark.parametrize(
    "background,expected",
    [
        ("rgb(250, 249, 247)", "light"),     # the hub's light surface
        ("rgb(13, 17, 23)", "dark"),         # the hub's dark surface
        ("rgb(255, 255, 255)", "light"),
        ("rgb(0, 0, 0)", "dark"),
        ("rgba(13, 17, 23, 0.8)", "dark"),   # the starfield canvas is translucent
        ("rgb(160, 160, 160)", "light"),     # clearly on the light side
        ("rgb(60, 60, 60)", "dark"),         # clearly on the dark side
        ("transparent", "unknown"),
        ("", "unknown"),
        ("#0d1117", "unknown"),              # not a computed colour: say so
    ],
)
def test_the_rendered_background_decides_the_theme(background, expected):
    # Arrange / Act / Assert: the light recording's pages read data-theme="light"
    # while the project workspace rendered near-black, so the pixels are the check.
    assert theme_from_background(background) == expected


def test_an_unreadable_background_is_not_reported_as_a_mismatch():
    # Arrange: a page that has not painted yet must not fail the theme check.
    # Act / Assert
    assert theme_from_background("rgba(0, 0, 0, 0)") in ("dark", "unknown")
