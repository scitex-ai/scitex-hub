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
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from demo_captions import (
    Chapter,
    TimedCaption,
    build_chapter_vtt,
    build_transcript,
    build_webvtt,
    wrap_caption,
)
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
    NARRATION_BACKENDS,
    NarrationClip,
    NarrationUnavailable,
    build_narration_track,
    synthesize_clip,
    voice_for,
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

    @property
    def chapter_vtt(self) -> Path:
        """The chapter track. Named `.chapters.vtt` so it is not read as captions."""
        return self.out_dir / f"{self.stem}.{self.language}.chapters.vtt"


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
    parser.add_argument("--narration-backend", default="gtts", choices=list(NARRATION_BACKENDS),
                        help="text-to-speech backend (elevenlabs needs a key and --voice)")
    parser.add_argument("--voice", default="",
                        help="voice name or id; gTTS defaults to the language code, "
                             "elevenlabs requires one (for example --voice sarah)")
    parser.add_argument("--theme", default="", choices=["", "light", "dark"],
                        help="put the recording in this theme and verify it (default: the "
                             "site's own default, which is dark)")
    parser.add_argument("--ffmpeg", default="", help="ffmpeg binary (default: PATH, env, wheel)")
    parser.add_argument("--ffprobe", default="", help="ffprobe binary (default: PATH, env)")
    parser.add_argument("--fonts-dir", default="",
                        help="extra font directory for the burned-in captions")
    parser.add_argument("--allow-stale", action="store_true",
                        help="record even when a selector no longer exists (recorded in the log)")
    parser.add_argument("--skip-manifest", action="store_true", help="do not write the manifest")
    parser.add_argument("--dry-run", action="store_true",
                        help="check selectors and print the matrix without recording")
    parser.add_argument("--preflight", action="store_true",
                        help="prove a render would work (sign-in, language switch, every page the "
                             "scenario opens) without changing anything; no clicks, no typing")
    return parser.parse_args()


def selected(requested: str, available: list[str]) -> list[str]:
    wanted = [name for name in requested.split(",") if name]
    return [name for name in available if not wanted or name in wanted]


def empty_selection_message(viewports: list[str], languages: list[str],
                            renditions: list[str], scenario: Scenario) -> str:
    """Why nothing would be recorded, and what the scenario offers instead.

    A `--viewports mobile` against a scenario that lists only desktop used to
    record nothing and still exit 0, with a manifest whose matrix was empty —
    measured 2026-09-17. An empty render that reports success is worse than a
    refusal: it looks like the mobile path was exercised.
    """
    return (
        f"nothing to record: viewports={viewports or 'none'}, "
        f"languages={languages or 'none'}, renditions={renditions or 'none'}; "
        f"the scenario offers viewports={list(scenario.viewports)}, "
        f"languages={list(scenario.languages)}, "
        f"renditions={[f'{item.language}:{item.ui_locale}' for item in scenario.renditions]}"
    )


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
                      tools: MediaTools, backend: str = "gtts",
                      narration_voice: str = "") -> tuple[dict, dict]:
    """Return {step_index: clip or None} and the seconds each step's narration needs."""
    clips, needed_seconds = {}, {}
    for index, step in enumerate(scenario.steps):
        text = step.narration.get(language, "")
        clip = (
            synthesize_clip(text, language, work_dir / f"{language}-{index:02d}.mp3", tools,
                            backend=backend, voice=narration_voice)
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


def language_matches(observed: str, locale: str) -> bool:
    """Whether a document's `lang` attribute is the locale that was asked for."""
    return bool(observed) and observed.lower().startswith(locale.lower())


def switch_ui_language(browser, base_url: str, storage_state, locale: str, path: str) -> dict:
    """Pick the language in the site's own switcher, as a visitor would.

    The check waits for the document to settle before it reads `lang`: measured
    2026-09-17, an unguarded read raced a slow response and came back empty
    (`left the page in '', not 'en'`), which failed a preflight while the render
    that followed succeeded. A flake in the guard is more expensive than in the
    render, because the guard is what people are told to trust.
    """
    context = browser.new_context(storage_state=storage_state)
    page = context.new_page()
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded", timeout=90_000)
    for attempt in (1, 2):
        page.click("#lang-select-trigger")
        with page.expect_navigation(timeout=60_000):
            page.click(f"form.lang-select-item:has(input[name=language][value={locale}]) button")
        try:
            page.wait_for_function(
                "() => document.readyState !== 'loading' "
                "&& (document.documentElement.lang || '').length > 0",
                timeout=15_000,
            )
        except Exception:
            pass
        active = page.evaluate("() => document.documentElement.lang || ''")
        if language_matches(active, locale):
            break
        if attempt == 2:
            context.close()
            raise RuntimeError(f"language switcher left the page in '{active}', not '{locale}'")
        page.wait_for_timeout(500)
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


def theme_init_script(theme: str) -> str:
    """The script that starts a recording in `theme`, using the product's own key.

    The hub's theme switcher (static/shared/ts/utils/theme-switcher.ts) persists the
    choice in localStorage under `stx-theme`, with the legacy hub key
    `scitex-theme-preference` still written for cached bundles. Writing those two
    keys is what a returning viewer's browser already has; it is not a bypass of the
    UI, and `apply_theme` additionally clicks the site's own toggle when the page
    does not come up in the requested theme, then verifies the result.

    The value is embedded with ``json.dumps`` so the generated script stays a valid
    JS string literal for any value it is handed, not just today's two.
    """
    literal = json.dumps(theme)
    return f"""
    (() => {{
      try {{
        localStorage.setItem('stx-theme', {literal});
        localStorage.setItem('scitex-theme-preference', {literal});
        document.documentElement.setAttribute('data-theme', {literal});
        document.documentElement.setAttribute('data-color-mode', {literal});
      }} catch (error) {{}}
    }})();
    """


def theme_from_background(rgb: str) -> str:
    """Which theme a computed CSS colour looks like: light, dark, or unknown.

    The attribute is a proxy — the dark-mode run of the light recording read
    `data-theme="light"` while the pixels were near-black, because parts of the
    product do not honour the theme. The computed background is the outcome, so the
    check reads it, and reports "unknown" rather than guessing when the value is not
    a parseable colour.
    """
    match = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+[\d.]+)?\s*\)",
                         (rgb or "").strip())
    if not match:
        return "unknown"
    red, green, blue = (float(value) for value in match.groups())
    # Rec. 601 luma, the cheap perceptual weighting; 0-255 scale.
    luma = 0.299 * red + 0.587 * green + 0.114 * blue
    return "light" if luma >= 128 else "dark"


def apply_theme(page, theme: str, base_url: str, switch_path: str) -> dict:
    """Put the recording in `theme` and verify it, clicking the site's toggle if not.

    Returns what actually happened, because a video that claims light mode and shows
    a dark page is worse than one that admits it could not switch: the manifest
    records the method, the verified page attribute AND the computed background, so a
    surface that ignores the theme shows up as `background_theme != theme` instead of
    being reported as a clean switch.
    """
    if not theme:
        return {"theme": "", "source": "site-default", "verified": False}

    def state() -> dict:
        observed = page.evaluate(
            """() => ({
                attribute: document.documentElement.getAttribute('data-theme') || '',
                background: getComputedStyle(document.body || document.documentElement)
                              .backgroundColor,
            })"""
        )
        observed["background_theme"] = theme_from_background(observed["background"])
        return observed

    current = state()
    source = "stored-preference"
    if current["attribute"] != theme:
        # Fall back to the control the product offers, if it is reachable here.
        try:
            toggle = page.locator("#theme-toggle").first
            if toggle.count() and toggle.is_visible():
                toggle.click()
                page.wait_for_timeout(500)
                source = "toggle-click"
        except Exception:
            pass
        current = state()
    return {
        "theme": theme,
        "source": source,
        "verified": current["attribute"] == theme,
        # The honest half: the page says light, but do the pixels?
        "background": current["background"],
        "background_theme": current["background_theme"],
        "background_matches": current["background_theme"] in (theme, "unknown"),
    }


class RecordingFailed(RuntimeError):
    """A step failed mid-render; the partial evidence is kept and described."""

    def __init__(self, report: dict):
        super().__init__(report.get("error", "recording failed"))
        self.report = report


def failure_report(recording: Recording, step_index: int, step, page_url: str,
                   error: Exception, timings: list[StepTiming]) -> dict:
    """What failed, where, and which selector: the shape a blocker needs.

    A step is optional: a render can fail before the first one is attempted.

    Measured 2026-09-17: a signed-in render died at the "open a file" step and left
    only a log — no video, no frame, no URL — so the report had to be reconstructed
    from a traceback. A failed render is still evidence, and it costs nothing to keep:
    the raw recording up to the failure is the most useful artifact a failure has.
    """
    return {
        "app": recording.scenario.app,
        "language": recording.language,
        "viewport": recording.viewport.name,
        "ui_locale": recording.rendition.ui_locale,
        "theme": getattr(step, "theme", ""),
        "step_index": step_index + 1 if step is not None else 0,
        "steps_total": len(recording.scenario.steps),
        "action": getattr(step, "action", ""),
        "selector": (step.selector.get(recording.language, "") if step is not None else ""),
        "value": (step.value.get(recording.language, "") if step is not None else ""),
        "page_url": page_url,
        "error": f"{type(error).__name__}: {error}".splitlines()[0][:400],
        "steps_completed": len(timings),
        "timings": [
            {"step": timing.step_index + 1, "start": round(timing.start_seconds, 3),
             "end": round(timing.end_seconds, 3)}
            for timing in timings
        ],
    }


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
    # Before the first paint: the site starts in the requested theme, the way a
    # returning viewer's browser already does.
    if args.theme:
        context.add_init_script(theme_init_script(args.theme))
    page = context.new_page()
    cursor = MovingCursor(page, viewport.width, viewport.height)
    # Scenarios that create things (a project name) need a fresh suffix per run.
    run_id = datetime.datetime.now().strftime("%H%M%S")
    recording_started = time.monotonic()
    timings = []
    theme_state = {"theme": args.theme, "source": "disabled", "verified": False}
    index: int = -1
    step = None
    try:
        for index, step in enumerate(recording.scenario.steps):
            if step.only not in ("", viewport.name):
                continue
            step_started = time.monotonic()
            run_step(page, cursor, step, recording.language, args, username, run_id)
            if index == first_visual_step(recording.scenario):
                # Once a page is on screen, verify the theme instead of trusting it.
                theme_state = apply_theme(page, args.theme, args.base_url,
                                          language_switch_path(recording.scenario))
            elapsed = time.monotonic() - step_started
            page.wait_for_timeout((max(needed_seconds[index] - elapsed, 0) + step.hold) * 1000)
            timings.append(
                StepTiming(index, step_started - recording_started,
                           time.monotonic() - recording_started)
            )
    except Exception as error:
        # Keep the partial evidence: the raw recording so far, where the page was, and
        # which control failed. A failed render must not be reconstructed from a
        # traceback by hand.
        report = failure_report(recording, index, step, page.url, error, timings)
        try:
            context.close()
            partial = recording.artifact("webm")
            shutil.move(page.video.path(), partial)
            report["partial_video"] = partial.name
        except Exception:
            report["partial_video"] = ""
        failure_path = recording.artifact("failure.json")
        failure_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
        report["report_path"] = str(failure_path)
        raise RecordingFailed(report) from error
    page.wait_for_timeout(1000)
    context.close()
    webm = recording.artifact("webm")
    shutil.move(page.video.path(), webm)
    return webm, timings, theme_state


def first_visual_step(scenario: Scenario) -> int:
    """The first step that leaves a page on screen, for the theme check."""
    for index, step in enumerate(scenario.steps):
        if step.action in ("goto", "click"):
            return index
    return 0


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


def chapters_for(recording: Recording, timings: list[StepTiming]) -> list[Chapter]:
    """The named spans of this recording, from the steps that declare a chapter.

    One list per recording, built from the same narration-driven timeline that
    times the captions, so an alternate UI-locale rendition carries the same
    chapter map even though it is a separate file.
    """
    chapters = []
    for timing in timings:
        title = recording.scenario.steps[timing.step_index].chapter.get(recording.language, "")
        if title:
            chapters.append(Chapter(title, timing.start_seconds, timing.end_seconds))
    return chapters


def artifact_role(path: Path) -> str:
    """What a recorded file is, by name: `.chapters.vtt` is not the caption file."""
    name = path.name
    if name.endswith(".chapters.vtt"):
        return "chapters"
    return {
        ".mp4": "video",
        ".webm": "raw",
        ".vtt": "captions",
        ".txt": "transcript",
        ".png": "thumbnail",
    }.get(path.suffix, path.suffix.lstrip("."))


def render(recording: Recording, webm: Path, timings, clips: dict[int, NarrationClip | None],
           work_dir: Path, tools: MediaTools, fonts_dir: str):
    """Write the captions, transcript, chapters, mp4 and thumbnail of one recording."""
    captions = captions_for(recording, timings)
    chapters = chapters_for(recording, timings)
    vtt = recording.artifact("vtt")
    vtt.write_text(build_webvtt(captions), encoding="utf-8")
    transcript = recording.artifact("txt")
    title = recording.scenario.title[recording.language]
    transcript.write_text(build_transcript(title, captions, chapters), encoding="utf-8")
    files = [webm, vtt, transcript]
    chapter_vtt = recording.chapter_vtt
    if chapters:
        chapter_vtt.write_text(build_chapter_vtt(chapters), encoding="utf-8")
        files.append(chapter_vtt)
    print(f"wrote {webm}, {vtt}, {transcript}"
          + (f" and {chapter_vtt}" if chapters else ""))
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
                    tools: MediaTools, clips: dict[int, NarrationClip | None],
                    theme_state: dict | None = None) -> dict:
    """The manifest view of one recording: digests, timing and narration length."""
    recorded = []
    for path in files:
        record = dict(file_digest(path))
        record["role"] = artifact_role(path)
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
        "theme": (theme_state or {}).get("theme", ""),
        "theme_source": (theme_state or {}).get("source", ""),
        "theme_verified": (theme_state or {}).get("verified", False),
        # What the pixels said: a surface that ignores the theme is recorded as such.
        "theme_background": (theme_state or {}).get("background", ""),
        "theme_background_theme": (theme_state or {}).get("background_theme", ""),
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


def preflight_targets(scenario: Scenario, username: str, run_id: str) -> list[str]:
    """Every page the scenario opens, with placeholders filled, in order."""
    return [target["path"] for target in preflight_target_kinds(scenario, username, run_id)]


def preflight_target_kinds(scenario: Scenario, username: str, run_id: str) -> list[dict]:
    """Every page the scenario opens, and whether it is supposed to exist yet.

    A page whose path carries `{run_id}` is created *during* the recording — that
    is what the placeholder is for — so requiring it to answer 200 before the
    render is wrong. Measured 2026-09-17 against the real demo account:
    `/beta-video-20260917-a/sleep-study-PREFLIGHT/` answered 404, preflight exited
    4, and the render that followed succeeded. A preflight that fails a render that
    works teaches people to ignore it, so the distinction is part of the check now.
    """
    targets: list[dict] = []
    for step in scenario.steps:
        if step.action != "goto":
            continue
        for value in step.value.values():
            # A localized value repeats the same string once per language; the page
            # is visited once, so the path is what de-duplicates (a created page
            # used to be added twice for exactly this reason).
            path = fill_placeholders(value, username, run_id)
            if any(entry["path"] == path for entry in targets):
                continue
            targets.append({"path": path, "creates": "{" in value})
    return targets


def run_preflight(scenario: Scenario, args, username: str, password: str) -> dict:
    """Prove a render would work, without changing anything on the site.

    The scenario's selectors are checked statically before this runs, so what is
    left is the part only a browser can answer: is the site up, does the demo
    account sign in, does the language switcher reach each rendition's locale, and
    does every page the scenario opens load. It never clicks or types, so it does
    not create a project, write a file or send a message — a preflight that had
    side effects would be useless for a signed-in scenario, because its first write
    is the thing you want to test.
    """
    from playwright.sync_api import sync_playwright

    run_id = "PREFLIGHT"
    targets = preflight_target_kinds(scenario, username, run_id)
    if any(target["creates"] for target in targets) and username:
        # The page a run creates cannot exist yet; the account's own area is the
        # thing that has to be reachable for the create to land somewhere.
        targets.append({"path": f"/{username}/", "creates": False})
    report = {
        "scenario": scenario.app,
        "base_url": args.base_url,
        "signed_in": None,
        "reachable": None,
        "language_switch": [],
        "pages": [],
        "pages_checked": "signed in" if scenario.sign_in else "signed out (no account needed)",
        "credentials": bool(username and password),
        "ready": False,
        "blockers": [],
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        state = None
        if scenario.sign_in and not (username and password):
            report["blockers"].append(
                "DEMO_USERNAME/DEMO_PASSWORD are not set, and this scenario starts signed in"
            )
        elif scenario.sign_in:
            try:
                state = sign_in(browser, args.base_url, username, password)
                report["signed_in"] = True
            except Exception as error:
                report["signed_in"] = False
                report["blockers"].append(f"sign-in failed: {type(error).__name__}: {error}")
        context = browser.new_context(storage_state=state) if state else browser.new_context()
        page = context.new_page()
        if scenario.sign_in and not state:
            # Without the account the scenario's pages are behind auth: visiting
            # them would only prove the redirect works, so say what was checked
            # and stop, instead of reporting pages that were never really seen.
            report["pages_checked"] = "not at all: no signed-in state"
            try:
                response = page.goto(f"{args.base_url}/", wait_until="domcontentloaded",
                                     timeout=90_000)
                report["reachable"] = bool(response) and response.status < 400
                if not report["reachable"]:
                    report["blockers"].append(
                        f"{args.base_url} answered HTTP {response.status if response else 0}"
                    )
            except Exception as error:
                report["reachable"] = False
                report["blockers"].append(f"{args.base_url} did not load: {type(error).__name__}")
            context.close()
            browser.close()
            report["ready"] = False
            return report
        switch_path = language_switch_path(scenario)
        for language, locale in scenario.locales.items():
            try:
                state = switch_ui_language(browser, args.base_url, state, locale, switch_path)
                report["language_switch"].append({"language": language, "locale": locale, "ok": True})
            except Exception as error:
                report["language_switch"].append(
                    {"language": language, "locale": locale, "ok": False,
                     "error": f"{type(error).__name__}: {error}"}
                )
                report["blockers"].append(f"language switcher did not reach '{locale}'")
        for target in targets:
            try:
                response = page.goto(f"{args.base_url}{target['path']}",
                                     wait_until="domcontentloaded", timeout=90_000)
                status = response.status if response else 0
                entry = {"path": target["path"], "status": status, "creates": target["creates"],
                         "ok": status < 400}
                if target["creates"]:
                    # A page this run creates is expected to be absent, and its
                    # absence is not a blocker: the render is what creates it.
                    entry["ok"] = True
                    entry["expected_absent"] = status >= 400
                report["pages"].append(entry)
                if not entry["ok"]:
                    report["blockers"].append(f"{target['path']} answered HTTP {status}")
            except Exception as error:
                report["pages"].append({"path": target["path"], "status": 0, "ok": False,
                                        "creates": target["creates"],
                                        "error": f"{type(error).__name__}: {error}"})
                report["blockers"].append(f"{target['path']} did not load: {type(error).__name__}")
        context.close()
        browser.close()
    report["ready"] = not report["blockers"]
    return report


def main() -> int:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    username = os.environ.get("DEMO_USERNAME", "")
    password = os.environ.get("DEMO_PASSWORD", "")
    # A dry run and a preflight record nothing, so neither needs the demo
    # credentials: they are how the matrix and the site are checked before a
    # signed-in render.
    if scenario.sign_in and not (username and password) and not (args.dry_run or args.preflight):
        print("Set DEMO_USERNAME and DEMO_PASSWORD for a scenario that signs in.")
        return 2

    stale_verdict, selector_report = check_selectors(scenario, args.allow_stale)
    if stale_verdict:
        return stale_verdict
    if args.preflight:
        report = run_preflight(scenario, args, username, password)
        print(json.dumps(report, indent=2, sort_keys=True))
        for blocker in report["blockers"]:
            print(f"BLOCKER: {blocker}", file=sys.stderr)
        print("preflight ready" if report["ready"] else "preflight NOT ready", file=sys.stderr)
        return 0 if report["ready"] else 4
    fonts_dir = args.fonts_dir or os.environ.get("SCITEX_DEMO_FONTS_DIR", "")
    if not caption_font_available(CAPTION_FONT, [fonts_dir] if fonts_dir else []):
        print(f"'{CAPTION_FONT}' is not installed: burned-in captions fall back to a font that "
              "may not have Japanese glyphs. Install it or set --fonts-dir.", file=sys.stderr)

    renditions = selected_renditions(args, scenario)
    viewports = selected(args.viewports, scenario.viewports)
    languages = selected(args.languages, scenario.languages)
    # Fail on an unusable voice before the render, not in the middle of it: a
    # backend that needs a named voice must not discover that fifteen minutes in.
    try:
        voice_for(args.narration_backend, args.voice, languages[0] if languages else "en")
    except NarrationUnavailable as reason:
        print(reason, file=sys.stderr)
        return 6
    if not viewports or not languages or not renditions:
        print(empty_selection_message(
            viewports, languages,
            [f"{item.language}:{item.ui_locale}" for item in renditions], scenario,
        ), file=sys.stderr)
        return 5
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
    voice = tools.has_ffmpeg and not args.no_voice

    narration = {}
    narration_failures = {}
    for language in languages:
        try:
            narration[language] = prepare_narration(
                scenario, language, work_dir, voice, tools,
                backend=args.narration_backend, narration_voice=args.voice,
            )
        except NarrationUnavailable as reason:
            print(f"No voice narration for {language}: {reason}. Rendering captions only.")
            narration_failures[language] = str(reason)
            narration[language] = prepare_narration(
                scenario, language, work_dir, voice=False, tools=tools,
                backend=args.narration_backend, narration_voice=args.voice,
            )
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
                try:
                    webm, timings, theme_state = record(browser, recording, state,
                                                        needed_seconds, args, username)
                except RecordingFailed as failure:
                    # The partial evidence is already on disk; say where and stop.
                    print(json.dumps(failure.report, indent=2, sort_keys=True))
                    print(f"render failed at step {failure.report['step_index']}"
                          f"/{failure.report['steps_total']}: {failure.report['error']}",
                          file=sys.stderr)
                    print(f"page: {failure.report['page_url']}", file=sys.stderr)
                    print(f"partial evidence: {failure.report.get('report_path', '')} "
                          f"{failure.report.get('partial_video', '')}", file=sys.stderr)
                    return 7
                mp4, files = render(recording, webm, timings, clips, work_dir, tools, fonts_dir)
                entries.append(rendition_entry(recording, timings, files, tools, clips,
                                               theme_state))
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
        tools_info=toolchain(tools, narration_backend=args.narration_backend if narrated else "",
                             narration_voice=args.voice, voice=narrated,
                             caption_font=CAPTION_FONT,
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
