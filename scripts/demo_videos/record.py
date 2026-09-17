#!/usr/bin/env python3
"""Replay a demo scenario YAML in Playwright and render narrated, captioned videos.

Run inside the dev container (Playwright, Chromium, ffmpeg and scitex_audio are there):

    DEMO_USERNAME=... DEMO_PASSWORD=... \
    python scripts/demo_videos/record.py scripts/demo_videos/scenarios/projects.yaml \
        --base-url http://127.0.0.1:8000 --out-dir media/videos/demos

Each viewport x language rendition in the scenario is a separate recording, made
with the site UI switched to that rendition's language through the site's own
language switcher. Every recording writes
<app>-<date>[-mobile][.ui-<locale>].<lang>.{webm,mp4,vtt,txt} and, on desktop, a
per-language thumbnail; the first desktop rendition also writes the catalog
thumbnail <app>-<date>-thumbnail.png. The run finishes by writing
<app>-<date>.manifest.json (reproducible metadata: commit, scenario digest,
toolchain, UI-contract fingerprint, per-file sha256) and an unwatched
<app>-<date>.watch-gate.json. See docs/ops/demo-videos.md.

The scenario's selectors are checked against the checkout before anything is
recorded: a control that moved, or a scenario selector that no longer exists,
stops the render instead of producing a video of the wrong screen.
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
from demo_manifest import (
    MANIFEST_SCHEMA,
    build_manifest,
    file_digest,
    manifest_path,
    summarize,
    toolchain,
    write_manifest,
)
from demo_narration import (
    NarrationClip,
    NarrationUnavailable,
    build_narration_track,
    synthesize_clip,
)
from demo_scenario import Rendition, Scenario, Step, load_scenario
from demo_selectors import (
    check_contracts,
    check_scenario,
    contract_fingerprint,
    missing_scenario_selectors,
)
from demo_tools import (
    MediaTools,
    caption_font_available,
    find_media_tools,
    media_duration,
)
from demo_watch_gate import gate_path, init_gate

POINTER_ACTIONS = {"click", "fill", "type", "hover"}
# Reading speed used to time steps when no voice is available, in characters per second.
FALLBACK_CHARACTERS_PER_SECOND = {"ja": 7.0}
DEFAULT_CHARACTERS_PER_SECOND = 15.0
CAPTION_FONT = "Noto Sans JP"
NARRATION_BACKEND = "gtts"
REPO_ROOT = Path(__file__).resolve().parents[2]


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
class Recording:
    scenario: Scenario
    viewport: Viewport
    rendition: Rendition
    out_dir: Path
    date: str

    @property
    def language(self) -> str:
        return self.rendition.language

    @property
    def stem(self) -> str:
        """The file-name stem shared by every artifact of this recording."""
        return (
            f"{self.scenario.app}-{self.date}{self.viewport.file_suffix}"
            f"{self.rendition.file_infix}"
        )

    def artifact(self, suffix: str) -> Path:
        return self.out_dir / f"{self.stem}.{self.language}.{suffix}"

    @property
    def thumbnail(self) -> Path:
        return self.out_dir / f"{self.stem}.{self.language}.thumbnail.png"


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
    parser.add_argument("--viewports", default="", help="subset of the scenario's viewports")
    parser.add_argument("--languages", default="", help="subset of the scenario's languages")
    parser.add_argument("--renditions", default="",
                        help="subset as language:ui_locale, e.g. ja:en (default: all)")
    parser.add_argument("--no-alternates", action="store_true",
                        help="skip the scenario's alternate UI-locale renditions")
    parser.add_argument("--no-voice", action="store_true", help="captions only, no TTS")
    parser.add_argument("--ffmpeg", default="", help="ffmpeg binary (default: PATH, env, wheel)")
    parser.add_argument("--ffprobe", default="", help="ffprobe binary (default: PATH, env)")
    parser.add_argument("--fonts-dir", default="",
                        help="extra font directory for the burned-in captions")
    parser.add_argument("--allow-stale", action="store_true",
                        help="record even when a selector no longer exists (recorded in the log)")
    parser.add_argument("--skip-manifest", action="store_true", help="do not write the manifest")
    parser.add_argument("--dry-run", action="store_true",
                        help="check selectors and print the matrix without recording")
    return parser.parse_args()


def selected(requested: str, available: list[str]) -> list[str]:
    wanted = [name for name in requested.split(",") if name]
    return [name for name in available if not wanted or name in wanted]


def selected_renditions(args, scenario: Scenario) -> list[Rendition]:
    """The renditions to record, in scenario order, minus the disabled ones."""
    wanted = {item for item in args.renditions.split(",") if item}
    renditions = []
    for rendition in scenario.renditions:
        if rendition.language not in selected(args.languages, scenario.languages):
            continue
        if rendition.canonical is False and args.no_alternates:
            continue
        if wanted and f"{rendition.language}:{rendition.ui_locale}" not in wanted:
            continue
        renditions.append(rendition)
    return renditions


def fill_placeholders(text: str, username: str, run_id: str) -> str:
    return text.replace("{username}", username).replace("{run_id}", run_id)


def estimated_speech_seconds(text: str, language: str) -> float:
    rate = FALLBACK_CHARACTERS_PER_SECOND.get(language, DEFAULT_CHARACTERS_PER_SECOND)
    return len(text) / rate


def check_selectors(scenario: Scenario, allow_stale: bool) -> tuple[int, dict]:
    """Refuse to record against a moved control; report fragile selectors."""
    statuses = [status for status in check_contracts(REPO_ROOT) if not status.ok]
    report = check_scenario(REPO_ROOT, scenario)
    missing = missing_scenario_selectors(report)
    for status in statuses:
        print(f"stale contract: {status.name} ({status.selector}) — {status.reason}")
    for selector in missing:
        print(f"stale selector: '{selector}' is in no template or script in the checkout")
    if statuses or missing:
        print("The scenario would record the wrong screen. Fix the scenario or the selector map;"
              " use --allow-stale only to capture evidence of the drift.", file=sys.stderr)
        return (0 if allow_stale else 3), report
    return 0, report


def prepare_narration(scenario: Scenario, language: str, work_dir: Path, voice: bool,
                      tools: MediaTools):
    """Return {step_index: clip or None} and the seconds each step's narration needs."""
    clips, needed_seconds = {}, {}
    for index, step in enumerate(scenario.steps):
        text = step.narration.get(language, "")
        clip = (
            synthesize_clip(text, language, work_dir / f"{language}-{index:02d}.mp3", tools)
            if voice and text
            else None
        )
        clips[index] = clip
        needed_seconds[index] = clip.duration_seconds if clip else estimated_speech_seconds(text, language)
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


def language_switch_path(scenario: Scenario) -> str:
    """A page the scenario itself opens, where the switch can be done.

    The switch used to happen on ``/apps/`` for every scenario, which is wrong for
    a signed-out tour (``/apps/`` redirects to signup) and fragile for a scenario
    that starts somewhere else. The first placeholder-free ``goto`` is a page the
    recording actually visits, so the language it is switched on is the same one.
    """
    for step in scenario.steps:
        if step.action != "goto":
            continue
        for value in step.value.values():
            if value and "{" not in value:
                return value
    return "/apps/"


def switch_ui_language(browser, base_url: str, storage_state, locale: str, path: str) -> dict:
    """Pick the language in the site's own switcher, as a visitor would."""
    context = browser.new_context(storage_state=storage_state)
    page = context.new_page()
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded", timeout=90_000)
    page.click("#lang-select-trigger")
    with page.expect_navigation(timeout=60_000):
        page.click(f"form.lang-select-item:has(input[name=language][value={locale}]) button")
    active = page.evaluate("() => document.documentElement.lang")
    if not active.startswith(locale):
        raise RuntimeError(f"language switcher left the page in '{active}', not '{locale}'")
    state = context.storage_state()
    context.close()
    return state


def run_step(page, cursor: MovingCursor, step: Step, language: str, args, username: str,
             run_id: str) -> None:
    selector = fill_placeholders(step.selector.get(language, ""), username, run_id)
    value = fill_placeholders(step.value.get(language, ""), username, run_id)
    locator = page.locator(selector).first if selector else None
    if step.action in POINTER_ACTIONS:
        cursor.glide_to(locator)
    if step.action == "goto":
        page.goto(f"{args.base_url}{value}", wait_until="domcontentloaded", timeout=90_000)
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


def record(browser, recording: Recording, storage_state, needed_seconds, args, username):
    viewport = recording.viewport
    video_dir = Path(tempfile.mkdtemp(prefix="demo-video-"))
    context = browser.new_context(
        viewport={"width": viewport.width, "height": viewport.height},
        is_mobile=viewport.is_mobile,
        has_touch=viewport.is_mobile,
        locale=recording.rendition.ui_locale,
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
    for index, step in enumerate(recording.scenario.steps):
        if step.only not in ("", viewport.name):
            continue
        step_started = time.monotonic()
        run_step(page, cursor, step, recording.language, args, username, run_id)
        elapsed = time.monotonic() - step_started
        page.wait_for_timeout((max(needed_seconds[index] - elapsed, 0) + step.hold) * 1000)
        timings.append(
            StepTiming(index, step_started - recording_started, time.monotonic() - recording_started)
        )
    page.wait_for_timeout(1000)
    context.close()
    webm = recording.artifact("webm")
    shutil.move(page.video.path(), webm)
    return webm, timings


def captions_for(recording: Recording, timings: list[StepTiming], line_width: int = 0):
    captions = []
    for timing in timings:
        text = recording.scenario.steps[timing.step_index].narration.get(recording.language, "")
        if line_width:
            text = wrap_caption(text, line_width)
        captions.append(TimedCaption(text, timing.start_seconds, timing.end_seconds))
    return captions


def encode_video(webm: Path, burn_vtt: Path, narration: Path | None, mp4: Path,
                 viewport: Viewport, tools: MediaTools, fonts_dir: str = "") -> None:
    style = (
        f"FontName={CAPTION_FONT},Fontsize={viewport.caption_font_size},BorderStyle=3,"
        f"Outline=4,Shadow=0,BackColour=&H99000000,MarginV={viewport.caption_margin_bottom}"
    )
    subtitle_filter = f"subtitles={burn_vtt}:force_style='{style}'"
    if fonts_dir:
        subtitle_filter = f"subtitles={burn_vtt}:fontsdir={fonts_dir}:force_style='{style}'"
    audio_input = ["-i", str(narration)] if narration else []
    audio_output = ["-map", "1:a", "-c:a", "aac"] if narration else []
    subprocess.run(
        [tools.ffmpeg, "-y", "-loglevel", "error", "-i", str(webm), *audio_input,
         "-vf", subtitle_filter, "-map", "0:v",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", *audio_output,
         "-movflags", "+faststart", str(mp4)],
        check=True,
    )


def extract_thumbnail(video: Path, png: Path, at_seconds: float, tools: MediaTools) -> None:
    subprocess.run(
        [tools.ffmpeg, "-y", "-loglevel", "error", "-ss", f"{at_seconds:.2f}", "-i", str(video),
         "-frames:v", "1", str(png)],
        check=True,
    )


def render(recording: Recording, webm: Path, timings, clips: dict[int, NarrationClip | None],
           work_dir: Path, tools: MediaTools, fonts_dir: str):
    """Write the captions, transcript, mp4 and thumbnail of one recording."""
    vtt = recording.artifact("vtt")
    vtt.write_text(build_webvtt(captions_for(recording, timings)), encoding="utf-8")
    transcript = recording.artifact("txt")
    title = recording.scenario.title[recording.language]
    transcript.write_text(build_transcript(title, captions_for(recording, timings)), encoding="utf-8")
    print(f"wrote {webm}, {vtt} and {transcript}")
    files = [webm, vtt, transcript]
    if not tools.has_ffmpeg:
        return None, files
    burn_vtt = work_dir / f"{recording.stem}.{recording.language}-burn.vtt"
    burn_vtt.write_text(
        build_webvtt(captions_for(recording, timings, recording.viewport.caption_line_width)),
        encoding="utf-8",
    )
    placed = [(clips[t.step_index].path, t.start_seconds) for t in timings if clips.get(t.step_index)]
    narration = None
    if placed:
        narration = work_dir / f"{recording.stem}.{recording.language}.m4a"
        build_narration_track(placed, media_duration(webm, tools), narration, tools.ffmpeg)
    mp4 = recording.artifact("mp4")
    encode_video(webm, burn_vtt, narration, mp4, recording.viewport, tools, fonts_dir)
    print(f"wrote {mp4}" + ("" if narration else " (no voice)"))
    files.append(mp4)
    if recording.viewport.name == "desktop":
        extract_thumbnail(mp4, recording.thumbnail, timings[-1].start_seconds + 0.5, tools)
        print(f"wrote {recording.thumbnail}")
        files.append(recording.thumbnail)
    return mp4, files


def rendition_entry(recording: Recording, timings: list[StepTiming], files: list[Path],
                    tools: MediaTools, clips: dict[int, NarrationClip | None]) -> dict:
    """The manifest view of one recording: digests, timing and narration length."""
    roles = {"mp4": "video", "webm": "raw", "vtt": "captions", "txt": "transcript",
             "thumbnail.png": "thumbnail"}
    recorded = []
    for path in files:
        suffix = path.name.rsplit(".", 1)[-1] if path.suffix != ".png" else "thumbnail.png"
        record = dict(file_digest(path))
        record["role"] = roles.get(suffix, suffix)
        recorded.append(record)
    duration = None
    if tools.has_ffprobe or tools.has_ffmpeg:
        video = next((path for path in files if path.suffix == ".mp4"), None)
        if video is not None:
            duration = round(media_duration(video, tools), 3)
    return {
        "language": recording.language,
        "ui_locale": recording.rendition.ui_locale,
        "canonical": recording.rendition.canonical,
        "alternate_reason": recording.rendition.reason,
        "viewport": recording.viewport.name,
        "duration_seconds": duration,
        "narration_seconds": round(sum(clip.duration_seconds for clip in clips.values() if clip), 3),
        "cues": sum(1 for timing in timings
                    if recording.scenario.steps[timing.step_index].narration.get(recording.language)),
        "timings": [
            {"step": timing.step_index + 1, "start": round(timing.start_seconds, 3),
             "end": round(timing.end_seconds, 3)}
            for timing in timings
        ],
        "files": recorded,
    }


def main() -> int:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    username = os.environ.get("DEMO_USERNAME", "")
    password = os.environ.get("DEMO_PASSWORD", "")
    # A dry run records nothing, so it must work without the demo credentials:
    # it is how you check the matrix and the selectors before a signed-in render.
    if scenario.sign_in and not (username and password) and not args.dry_run:
        print("Set DEMO_USERNAME and DEMO_PASSWORD for a scenario that signs in.")
        return 2

    stale_verdict, selector_report = check_selectors(scenario, args.allow_stale)
    if stale_verdict:
        return stale_verdict
    fonts_dir = args.fonts_dir or os.environ.get("SCITEX_DEMO_FONTS_DIR", "")
    if not caption_font_available(CAPTION_FONT, [fonts_dir] if fonts_dir else []):
        print(f"'{CAPTION_FONT}' is not installed: burned-in captions fall back to a font that "
              "may not have Japanese glyphs. Install it or set --fonts-dir.", file=sys.stderr)

    renditions = selected_renditions(args, scenario)
    viewports = selected(args.viewports, scenario.viewports)
    if args.dry_run:
        for rendition in renditions:
            print(f"would record {rendition.language} narration over '{rendition.ui_locale}' UI"
                  f"{'' if rendition.canonical else ' (alternate: ' + rendition.reason + ')'}")
        print(f"viewports: {viewports}")
        return 0

    tools = find_media_tools()
    if args.ffmpeg:
        tools = MediaTools(args.ffmpeg, tools.ffprobe, "command line")
    if args.ffprobe:
        tools = MediaTools(tools.ffmpeg, args.ffprobe, tools.source)
    if not tools.has_ffmpeg:
        print("ffmpeg not found: keeping the webm, .vtt and .txt files; no mp4, no voice.")
    if not tools.has_ffprobe:
        print("ffprobe not found: durations come from `ffmpeg -i`; the TTS backend "
              "(pydub) needs ffprobe on PATH, so narration may fall back to captions only.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="demo-narration-"))
    languages = selected(args.languages, scenario.languages)
    voice = tools.has_ffmpeg and not args.no_voice

    narration = {}
    narration_failures = {}
    for language in languages:
        try:
            narration[language] = prepare_narration(scenario, language, work_dir, voice, tools)
        except NarrationUnavailable as reason:
            print(f"No voice narration for {language}: {reason}. Rendering captions only.")
            narration_failures[language] = str(reason)
            narration[language] = prepare_narration(scenario, language, work_dir, voice=False,
                                                    tools=tools)
    # The manifest records what actually happened, not what was asked for: a
    # silent mp4 with `voice: true` in its metadata is a lie a reviewer cannot see.
    narrated = any(
        clip is not None
        for clips, _needed in narration.values()
        for clip in clips.values()
    )

    from playwright.sync_api import sync_playwright

    switch_path = language_switch_path(scenario)
    entries = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        signed_in = sign_in(browser, args.base_url, username, password) if scenario.sign_in else None
        for viewport_name in viewports:
            viewport = VIEWPORTS[viewport_name]
            for rendition in renditions:
                recording = Recording(scenario, viewport, rendition, args.out_dir, args.date)
                state = switch_ui_language(browser, args.base_url, signed_in, rendition.ui_locale,
                                           switch_path)
                clips, needed_seconds = narration[rendition.language]
                webm, timings = record(browser, recording, state, needed_seconds, args, username)
                mp4, files = render(recording, webm, timings, clips, work_dir, tools, fonts_dir)
                entries.append(rendition_entry(recording, timings, files, tools, clips))
                if viewport.name == "desktop" and rendition.language == scenario.languages[0]:
                    catalog_png = args.out_dir / f"{scenario.app}-{args.date}-thumbnail.png"
                    if mp4 and not catalog_png.exists():
                        extract_thumbnail(mp4, catalog_png, timings[-1].start_seconds + 0.5, tools)
                        print(f"wrote {catalog_png}")
        browser.close()

    if args.skip_manifest:
        return 0
    manifest = build_manifest(
        app=scenario.app,
        date=args.date,
        titles=dict(scenario.title),
        scenario_path=args.scenario,
        repo_root=REPO_ROOT,
        base_url=args.base_url,
        renditions=entries,
        tools_info=toolchain(tools, narration_backend=NARRATION_BACKEND if narrated else "",
                             voice=narrated, caption_font=CAPTION_FONT,
                             font_available=caption_font_available(CAPTION_FONT, [fonts_dir] if fonts_dir else []),
                             narration_failures=narration_failures),
        contracts={"fingerprint": contract_fingerprint(),
                   "contracts": {status.name: status.version for status in check_contracts(REPO_ROOT)},
                   "selector_check": selector_report,
                   "schema": "scitex.demo-video.ui-contract/1"},
        viewports=viewports,
        languages=languages,
        steps=len(scenario.steps),
    )
    path = write_manifest(manifest_path(args.out_dir, scenario.app, args.date), manifest)
    print(f"wrote {path}")
    gate = gate_path(args.out_dir, scenario.app, args.date)
    gate_written = init_gate(manifest, path=gate)
    print(f"wrote {gate} — publish requires a watch of both languages:")
    for language in gate_written["required_languages"]:
        artifact = gate_written["artifacts"].get(language, {}).get("name", "no video file")
        print(f"  {language}: {artifact}")
    print(f"manifest schema {MANIFEST_SCHEMA}: " + str(summarize(manifest)["renditions"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
