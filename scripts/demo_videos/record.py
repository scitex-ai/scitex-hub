#!/usr/bin/env python3
"""Replay a demo scenario YAML in Playwright and render narrated, captioned videos.

Run inside the dev container (Playwright, Chromium, ffmpeg and scitex_audio are there):

    DEMO_USERNAME=... DEMO_PASSWORD=... \
    python scripts/demo_videos/record.py scripts/demo_videos/scenarios/projects.yaml \
        --base-url http://127.0.0.1:8000 --out-dir media/videos/demos

For every viewport (1280x720 desktop, 390x844 mobile) and every scenario language
it writes <app>-<date>[-mobile].<lang>.{mp4,vtt,txt}, plus the raw .webm and a
<app>-<date>-thumbnail.png. See docs/ops/demo-videos.md.
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from demo_captions import TimedCaption, build_transcript, build_webvtt, wrap_caption
from demo_cursor import CURSOR_OVERLAY_SCRIPT, MovingCursor
from demo_narration import (
    NarrationUnavailable,
    build_narration_track,
    media_duration,
    synthesize_clip,
)
from demo_scenario import Scenario, Step, load_scenario

POINTER_ACTIONS = {"click", "fill", "type", "hover"}
# Reading speed used to time steps when no voice is available, in characters per second.
FALLBACK_CHARACTERS_PER_SECOND = {"ja": 7.0}
DEFAULT_CHARACTERS_PER_SECOND = 15.0
CAPTION_FONT = "Noto Sans JP"


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int
    is_mobile: bool
    file_suffix: str
    caption_font_size: int
    caption_margin_bottom: int
    caption_line_width: int


# Caption sizes are libass units on a 288-line canvas, scaled to the video height;
# the bottom margin keeps captions above the site dock. Line width is in half-width
# character cells (a Japanese character counts as two).
VIEWPORTS = {
    "desktop": Viewport("desktop", 1280, 720, False, "", 15, 40, 58),
    "mobile": Viewport("mobile", 390, 844, True, "-mobile", 8, 36, 30),
}


@dataclass(frozen=True)
class StepTiming:
    step_index: int
    start_seconds: float
    end_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out-dir", type=Path, default=Path("media/videos/demos"))
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--viewports", default="desktop,mobile")
    parser.add_argument("--no-voice", action="store_true", help="captions only, no TTS")
    return parser.parse_args()


def fill_placeholders(text: str, username: str, run_id: str) -> str:
    return text.replace("{username}", username).replace("{run_id}", run_id)


def estimated_speech_seconds(text: str, language: str) -> float:
    rate = FALLBACK_CHARACTERS_PER_SECOND.get(language, DEFAULT_CHARACTERS_PER_SECOND)
    return len(text) / rate


def prepare_narration(scenario: Scenario, work_dir: Path, voice: bool):
    """Return {(step_index, language): clip or None} and seconds each step must last."""
    clips, needed_seconds = {}, {}
    for index, step in enumerate(scenario.steps):
        durations = [0.0]
        for language, text in step.narration.items():
            clip = None
            if voice:
                clip = synthesize_clip(text, language, work_dir / f"{language}-{index:02d}.mp3")
            clips[(index, language)] = clip
            durations.append(clip.duration_seconds if clip else estimated_speech_seconds(text, language))
        needed_seconds[index] = max(durations)
    return clips, needed_seconds


def sign_in(browser, base_url: str, username: str, password: str) -> dict:
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#login-form button[type=submit]")
    page.wait_for_url(lambda url: "/auth/signin" not in url, timeout=60_000)
    state = context.storage_state()
    context.close()
    return state


def run_step(page, cursor: MovingCursor, step: Step, base_url: str, username: str, run_id: str) -> None:
    selector = fill_placeholders(step.selector, username, run_id)
    value = fill_placeholders(step.value, username, run_id)
    locator = page.locator(selector).first if selector else None
    if step.action in POINTER_ACTIONS:
        cursor.glide_to(locator)
    if step.action == "goto":
        page.goto(f"{base_url}{value}", wait_until="domcontentloaded", timeout=90_000)
    elif step.action == "click":
        locator.click()
    elif step.action == "fill":
        locator.fill(value)
    elif step.action == "type":
        locator.press_sequentially(value, delay=45)
    elif step.action == "press":
        (locator or page.keyboard).press(value)
    elif step.action == "hover":
        locator.hover()
    elif step.action == "scroll":
        page.mouse.wheel(0, int(value or 400))


def record_viewport(browser, scenario, viewport, storage_state, needed_seconds, args, username):
    video_dir = Path(tempfile.mkdtemp(prefix="demo-video-"))
    context = browser.new_context(
        viewport={"width": viewport.width, "height": viewport.height},
        is_mobile=viewport.is_mobile,
        has_touch=viewport.is_mobile,
        record_video_dir=str(video_dir),
        record_video_size={"width": viewport.width, "height": viewport.height},
        storage_state=storage_state,
    )
    context.add_init_script(CURSOR_OVERLAY_SCRIPT)
    page = context.new_page()
    cursor = MovingCursor(page, viewport.width, viewport.height)
    # Scenarios that create things (a project name) need a fresh suffix per run.
    run_id = datetime.datetime.now().strftime("%H%M%S")
    recording_started = time.monotonic()
    timings = []
    for index, step in enumerate(scenario.steps):
        if step.only not in ("", viewport.name):
            continue
        step_started = time.monotonic()
        run_step(page, cursor, step, args.base_url, username, run_id)
        elapsed = time.monotonic() - step_started
        page.wait_for_timeout(max(needed_seconds[index] - elapsed, 0) * 1000 + step.hold * 1000)
        timings.append(
            StepTiming(index, step_started - recording_started, time.monotonic() - recording_started)
        )
    page.wait_for_timeout(1000)
    context.close()
    return Path(page.video.path()), timings


def captions_for(scenario: Scenario, timings: list[StepTiming], language: str, line_width: int = 0):
    captions = []
    for timing in timings:
        text = scenario.steps[timing.step_index].narration.get(language, "")
        if line_width:
            text = wrap_caption(text, line_width)
        captions.append(TimedCaption(text, timing.start_seconds, timing.end_seconds))
    return captions


def encode_video(webm: Path, burn_vtt: Path, narration: Path | None, mp4: Path, viewport: Viewport) -> None:
    style = (
        f"FontName={CAPTION_FONT},Fontsize={viewport.caption_font_size},BorderStyle=3,"
        f"Outline=4,Shadow=0,BackColour=&H99000000,MarginV={viewport.caption_margin_bottom}"
    )
    audio_input = ["-i", str(narration)] if narration else []
    audio_output = ["-map", "1:a", "-c:a", "aac"] if narration else []
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), *audio_input,
         "-vf", f"subtitles={burn_vtt}:force_style='{style}'", "-map", "0:v",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", *audio_output,
         "-movflags", "+faststart", str(mp4)],
        check=True,
    )


def extract_thumbnail(video: Path, png: Path, at_seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at_seconds:.2f}", "-i", str(video),
         "-frames:v", "1", str(png)],
        check=True,
    )


def render_language(scenario, viewport, timings, language, clips, webm, stem, work_dir, has_ffmpeg):
    vtt = stem.with_name(f"{stem.name}.{language}.vtt")
    vtt.write_text(build_webvtt(captions_for(scenario, timings, language)), encoding="utf-8")
    transcript = stem.with_name(f"{stem.name}.{language}.txt")
    transcript.write_text(
        build_transcript(scenario.title[language], captions_for(scenario, timings, language)),
        encoding="utf-8",
    )
    print(f"wrote {vtt} and {transcript}")
    if not has_ffmpeg:
        return None
    burn_vtt = work_dir / f"{viewport.name}-{language}-burn.vtt"
    burn_vtt.write_text(
        build_webvtt(captions_for(scenario, timings, language, viewport.caption_line_width)),
        encoding="utf-8",
    )
    placed = [
        (clips[(timing.step_index, language)].path, timing.start_seconds)
        for timing in timings
        if clips.get((timing.step_index, language))
    ]
    narration = None
    if placed:
        narration = work_dir / f"{viewport.name}-{language}.m4a"
        build_narration_track(placed, media_duration(webm), narration)
    mp4 = stem.with_name(f"{stem.name}.{language}.mp4")
    encode_video(webm, burn_vtt, narration, mp4, viewport)
    print(f"wrote {mp4}" + ("" if narration else " (no voice)"))
    return mp4


def main() -> int:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    username = os.environ.get("DEMO_USERNAME", "")
    password = os.environ.get("DEMO_PASSWORD", "")
    if scenario.sign_in and not (username and password):
        print("Set DEMO_USERNAME and DEMO_PASSWORD for a scenario that signs in.")
        return 2
    has_ffmpeg = shutil.which("ffmpeg") is not None
    if not has_ffmpeg:
        print("ffmpeg not found: keeping the webm, .vtt and .txt files; no mp4, no voice.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="demo-narration-"))

    voice = has_ffmpeg and not args.no_voice
    try:
        clips, needed_seconds = prepare_narration(scenario, work_dir, voice)
    except NarrationUnavailable as reason:
        print(f"No voice narration: {reason}. Rendering captions only.")
        clips, needed_seconds = prepare_narration(scenario, work_dir, voice=False)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        storage_state = sign_in(browser, args.base_url, username, password) if scenario.sign_in else None
        for name in args.viewports.split(","):
            viewport = VIEWPORTS[name]
            stem = args.out_dir / f"{scenario.app}-{args.date}{viewport.file_suffix}"
            raw_video, timings = record_viewport(
                browser, scenario, viewport, storage_state, needed_seconds, args, username
            )
            webm = stem.with_suffix(".webm")
            shutil.move(raw_video, webm)
            for language in scenario.languages:
                mp4 = render_language(
                    scenario, viewport, timings, language, clips, webm, stem, work_dir, has_ffmpeg
                )
                if mp4 and viewport.name == "desktop" and language == scenario.languages[0]:
                    thumbnail = args.out_dir / f"{scenario.app}-{args.date}-thumbnail.png"
                    extract_thumbnail(mp4, thumbnail, timings[-1].start_seconds + 0.5)
                    print(f"wrote {thumbnail}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
