"""The demo player must keep the viewer's place when the language changes.

The narrated guides ship as one video per language, so the language switch swaps
a file. Swapping a file restarts playback unless the switch restores position,
rate, playing state and captions. That behaviour lives in one plain script the
template loads, and it is verified against real media by
scripts/demo_videos/verify_playback.py.

These tests are the cheap half: the template must hand the script everything it
needs (the rendition list, the starting language, the caption language), the
script must implement every step of the restore, and the file the template points
at must be the file that exists — a rename cannot silently drop the switch.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPO_ROOT / "apps/infra/public_app/templates/public_app/pages/video_player.html"
PLAYER_SCRIPT = REPO_ROOT / "apps/infra/public_app/static/public_app/js/demo-video-player.js"
VIEWS = REPO_ROOT / "apps/infra/public_app/views/pages.py"
VERIFIER = REPO_ROOT / "scripts/demo_videos/verify_playback.py"


def template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def script() -> str:
    return PLAYER_SCRIPT.read_text(encoding="utf-8")


def test_the_player_script_exists_where_the_template_loads_it_from():
    # Arrange
    source = template()
    # Act
    referenced = re.findall(r"static '([^']*demo-video-player\.js)'", source)
    # Assert
    assert referenced == ["public_app/js/demo-video-player.js"]
    assert PLAYER_SCRIPT.is_file(), "the template's script must be on disk"


def test_the_template_hands_the_script_the_rendition_list():
    # Arrange / Act
    source = template()
    # Assert
    assert 'data-languages="{{ video_languages_json }}"' in source
    assert 'data-default-language="{{ video_default_language }}"' in source
    assert 'data-default-captions="{{ video_default_captions }}"' in source
    # One control per rendition, keyed by the rendition code the script switches on.
    assert 'data-demo-lang="{{ language.code }}"' in source
    # A live region so the switch is announced, not silent.
    assert 'id="demo-video-language-status"' in source
    assert 'aria-live="polite"' in source


def test_the_language_controls_are_only_shown_when_there_is_a_choice():
    # Arrange / Act
    source = template()
    # Assert
    assert "{% if video_languages|length > 1 %}" in source


def test_the_view_passes_the_renditions_and_the_caption_default():
    # Arrange / Act
    source = VIEWS.read_text(encoding="utf-8")
    # Assert
    assert "languages_for(" in source
    assert '"video_languages_json"' in source
    assert "default_language(" in source and "default_captions(" in source


def test_the_script_restores_position_rate_and_playing_state():
    # Arrange / Act
    source = script()
    # Assert: every part of the restore is present, in the switch itself.
    assert "video.currentTime = wanted" in source
    assert "video.playbackRate = rate" in source
    assert "video.addEventListener('loadedmetadata', restore)" in source
    assert "var wasPlaying = !video.paused && !video.ended" in source
    assert "video.load()" in source


def test_the_script_switches_the_caption_track_with_the_audio():
    # Arrange / Act
    source = script()
    # Assert
    assert "track.mode = language === code && code ? 'showing' : 'disabled'" in source
    assert "captionCode" in source, "captions follow the narration language"


def test_the_script_reports_what_the_switch_did_for_verification():
    # Arrange / Act
    source = script()
    # Assert
    assert "window.demoVideoPlayer" in source
    assert "demo-video-language-changed" in source
    assert "withinTolerance" in source


def test_the_script_only_swaps_the_file_when_the_target_differs():
    # Arrange / Act
    source = script()
    # Assert: choosing the language you are already on must not reload the video.
    assert "if (code === activeRendition(video))" in source


def test_the_verifier_measures_position_rather_than_assuming_it():
    # Arrange / Act
    source = VERIFIER.read_text(encoding="utf-8")
    # Assert
    for check in (
        "position_preserved",
        "playback_rate_preserved",
        "pause_state_preserved",
        "captions_switched",
        "language_switched",
        "playback_advanced",
    ):
        assert check in source, check
    assert "demoVideoPlayer.state()" in source
    assert "PLAYER_SCRIPT" in source
