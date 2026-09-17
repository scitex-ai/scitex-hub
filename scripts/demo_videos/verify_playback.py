#!/usr/bin/env python3
"""Play back a recorded rendition in Chromium and prove the language switch keeps its place.

The card asks for "player audio/subtitle switch without losing position" and for
real playback evidence. Asserting on the template's markup proves neither, so this
script loads the *shipped* player script
(``apps/infra/public_app/static/public_app/js/demo-video-player.js``) into a real
Chromium against the *recorded* media files and measures what happens:

1. play, seek into the middle of the walkthrough, set a non-default playback rate;
2. switch the narration/subtitle language the way a viewer does (click);
3. check the new file, the caption track and the delivered position.

It writes a JSON verdict next to nothing else, and exits 1 when a check fails, so
the gate is a command and not an opinion.

Two modes:

* ``--manifest <render>/<app>-<date>.manifest.json`` builds a local harness page
  from the recorded renditions and serves it over http; this is the evidence a
  render can produce on its own.
* ``--page-url <url>`` drives the real product page. It reports
  ``not_deployed`` unless that page already carries the rendition list, so a
  missing deploy is stated rather than assumed.
"""

import argparse
import functools
import http.server
import json
import os
import shutil
import socket
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYER_SCRIPT = REPO_ROOT / "apps/infra/public_app/static/public_app/js/demo-video-player.js"
PLAYER_ID = "demo-video"
LANGUAGE_EVENT = "demo-video-language-changed"
# A seek lands on the nearest keyframe, so the delivered position is expected to
# be a fraction of a second away from the requested one.
DEFAULT_TOLERANCE_SECONDS = 0.75

HARNESS_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>demo player harness</title></head>
<body>
<video id="{player_id}" controls preload="auto"
       data-default-speed="1"
       data-default-language="{default_language}"
       data-default-captions=""
       data-languages="{languages}">
  <source src="{first_src}" type="video/mp4" />
{caption_tracks}
</video>
<div role="group" aria-label="narration language">
{buttons}
</div>
<p id="demo-video-language-status" role="status" aria-live="polite"></p>
<script src="demo-video-player.js"></script>
</body>
</html>
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play back a recorded rendition and check the language switch keeps its place"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path, help="render manifest to play back")
    source.add_argument("--page-url", help="a real player page to drive")
    parser.add_argument("--media-dir", type=Path, default=None,
                        help="directory with the recorded files (default: the manifest's)")
    parser.add_argument("--language", default="", help="start language code (default: first)")
    parser.add_argument("--switch-to", default="", help="language code to switch to")
    parser.add_argument("--seek-seconds", type=float, default=0.0,
                        help="seek here before switching (default: 40%% of the video)")
    parser.add_argument("--playback-rate", type=float, default=1.25)
    parser.add_argument("--play-seconds", type=float, default=1.5)
    parser.add_argument("--tolerance-seconds", type=float, default=DEFAULT_TOLERANCE_SECONDS)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--verbose", action="store_true",
                        help="log the harness requests and the media element's state")
    return parser.parse_args(argv)


def classify_range(range_header: str, size: int) -> tuple[int, int] | None:
    """Parse `bytes=start-end` into a byte range, or None when unusable."""
    if not range_header or not range_header.startswith("bytes="):
        return None
    spec = range_header[len("bytes="):].split(",")[0].strip()
    start_text, _, end_text = spec.partition("-")
    try:
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        else:
            # A suffix range: the last N bytes.
            start = max(size - int(end_text), 0)
            end = size - 1
    except ValueError:
        return None
    start = max(start, 0)
    end = min(end, size - 1)
    if start > end:
        return None
    return start, end


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A static handler that honours Range requests.

    Python's SimpleHTTPRequestHandler answers 200 with the whole file and no
    ``Accept-Ranges``. Chromium then cannot seek: it asks for a byte range, gets
    the whole file back, and silently keeps playing from wherever it was. A
    verification harness built on that server reports a perfect position restore
    that never happened — measured, 2026-09-17, before this handler existed.
    """

    protocol_version = "HTTP/1.1"
    range_length: int | None = None
    quiet = True

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        if not self.quiet:
            super().log_message(format, *args)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            self.range_length = None
            handle = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        size = os.fstat(handle.fileno()).st_size
        content_type = self.guess_type(path)
        byte_range = classify_range(self.headers.get("Range", ""), size)
        if byte_range is None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return handle
        start, end = byte_range
        self.range_length = end - start + 1
        handle.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self.range_length))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        return handle

    def copyfile(self, source, outputfile):
        if self.range_length is None:
            return super().copyfile(source, outputfile)
        remaining = self.range_length
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def serve(directory: Path, quiet: bool = True) -> tuple[socketserver.TCPServer, str]:
    handler = functools.partial(RangeRequestHandler, directory=str(directory))
    RangeRequestHandler.quiet = quiet
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", free_port()), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def video_files(manifest: dict, media_dir: Path, role: str = "video") -> list[dict]:
    """One entry per playable rendition: {code, label, src, captions}, files on disk.

    ``role`` picks which recorded file to play: the published mp4, or the raw
    Playwright webm. The open-source Chromium build has no H.264 decoder, so a
    machine without licensed codecs verifies the same timeline through the webm —
    which is the file the captions and the narration were timed against anyway.
    """
    fallback_roles = [role] + [other for other in ("video", "raw") if other != role]
    renditions = []
    for rendition in manifest.get("renditions", []):
        if rendition.get("viewport", "desktop") != "desktop":
            continue
        files = {record["role"]: record for record in rendition.get("files", [])}
        chosen = ""
        for candidate in fallback_roles:
            record = files.get(candidate)
            if record and (media_dir / record["name"]).exists():
                chosen = record["name"]
                break
        if not chosen:
            continue
        captions = files.get("captions", {})
        code = rendition["language"]
        ui_locale = rendition.get("ui_locale", code)
        renditions.append(
            {
                "code": code if ui_locale == code else f"{code}@{ui_locale}",
                "language": code,
                "label": {"en": "English", "ja": "日本語"}.get(code, code.upper()),
                "src": chosen,
                "captions": captions.get("name", ""),
                "captionCode": code,
                "canonical": ui_locale == code,
                "ui_locale": ui_locale,
            }
        )
    return renditions


def build_harness(renditions: list[dict], media_dir: Path, default_language: str) -> Path:
    """A page with the player's DOM contract, the shipped script and the real files."""
    harness_dir = Path(tempfile.mkdtemp(prefix="demo-playback-"))
    for rendition in renditions:
        for name in (rendition["src"], rendition["captions"]):
            if name:
                shutil.copy(media_dir / name, harness_dir / name)
    shutil.copy(PLAYER_SCRIPT, harness_dir / "demo-video-player.js")
    tracks = "\n".join(
        f'  <track kind="captions" src="{rendition["captions"]}" '
        f'srclang="{rendition["captionCode"]}" label="{rendition["label"]}" />'
        for rendition in renditions
        if rendition["captions"]
    )
    buttons = "\n".join(
        f'<button type="button" data-demo-lang="{rendition["code"]}">{rendition["label"]}</button>'
        for rendition in renditions
    )
    page = HARNESS_PAGE.format(
        player_id=PLAYER_ID,
        default_language=default_language,
        languages=json.dumps(renditions, ensure_ascii=False).replace('"', "&quot;"),
        first_src=renditions[0]["src"] if renditions else "",
        caption_tracks=tracks,
        buttons=buttons,
    )
    (harness_dir / "index.html").write_text(page, encoding="utf-8")
    return harness_dir


def measure(page, script_wait_ms: int = 10_000) -> dict:
    """Play, switch language, and return what the switch did to the playback."""
    page.wait_for_function("() => !!window.demoVideoPlayer", timeout=script_wait_ms)
    started = page.evaluate(
        """() => {
            const video = document.getElementById('demo-video');
            return {duration: video.duration, paused: video.paused,
                    languages: window.demoVideoPlayer.languages.map(l => l.code)};
        }"""
    )
    return started


def run_switch(page, switch_to: str, args) -> dict:
    """The measured switch: seek, play, click the language, read the state back.

    The decisive measurement is taken at the instant the player announces the
    switch, not after a sleep or after waiting for the clock to arrive somewhere.
    Both of those hid a real defect: with the position restore broken, the media
    element restarts at zero and the clock reaches the old position again by
    playing forward — measured 2026-09-17, a harness that slept through this
    reported a 0.74 s drift and called it a pass.
    """
    page.wait_for_function(
        "() => { const v = document.getElementById('demo-video'); return isFinite(v.duration) && v.duration > 0; }",
        timeout=30_000,
    )
    page.evaluate(
        """([seconds, rate]) => {
            const video = document.getElementById('demo-video');
            const target = seconds > 0 ? seconds : video.duration * 0.4;
            video.currentTime = Math.min(target, Math.max(video.duration - 1, 0));
            video.playbackRate = rate;
        }""",
        [args.seek_seconds, args.playback_rate],
    )
    page.wait_for_function(
        """() => { const v = document.getElementById('demo-video'); return !v.seeking; }""",
        timeout=15_000,
    )
    page.evaluate("() => document.getElementById('demo-video').play()")
    page.wait_for_timeout(int(args.play_seconds * 1000))
    clicked = page.evaluate(
        """(selector) => {
            const video = document.getElementById('demo-video');
            const before = {
                position: video.currentTime,
                paused: video.paused,
                playbackRate: video.playbackRate,
                duration: video.duration,
                src: video.currentSrc,
                captionsLanguage: window.demoVideoPlayer.state().captionsLanguage,
                language: window.demoVideoPlayer.state().language,
            };
            document.querySelector(`button[data-demo-lang="${selector}"]`).click();
            return before;
        }""",
        switch_to,
    )
    switched = page.evaluate(
        """() => new Promise(resolve => {
            const listener = (event) => {
                const video = document.getElementById('demo-video');
                const state = window.demoVideoPlayer.state();
                resolve({
                    detail: event.detail,
                    at: video.currentTime,
                    paused: video.paused,
                    playbackRate: video.playbackRate,
                    duration: video.duration,
                    src: video.currentSrc,
                    readyState: video.readyState,
                    captionsLanguage: state.captionsLanguage,
                    language: state.language,
                });
            };
            document.addEventListener('demo-video-language-changed', listener, {once: true});
            setTimeout(() => resolve(null), 20_000);
        })"""
    )
    if switched is None:
        return {"before": clicked, "after": {}, "advanced": {}, "announced": False}
    page.wait_for_timeout(int(args.play_seconds * 1000))
    advanced = page.evaluate("() => window.demoVideoPlayer.state()")
    return {"before": clicked, "after": switched, "advanced": advanced, "announced": True}


def checks_from(measured: dict, target: dict, args, seconds_played: float) -> dict:
    """Judge the switch from what was measured at the switch, not from a later state."""
    before, after, advanced = measured["before"], measured["after"], measured["advanced"]
    if not measured.get("announced") or not after:
        return {
            "position_preserved": False,
            "position_drift_seconds": None,
            "playback_rate_preserved": False,
            "pause_state_preserved": False,
            "captions_switched": False,
            "captions_language": "",
            "language_switched": False,
            "playback_advanced": False,
            "advanced_seconds": 0.0,
            "announced": False,
        }
    drift = after["at"] - before["position"]
    source_switched = Path(target.get("src", "")).name in (after.get("src") or "")
    return {
        # The position at the instant the player announced the switch. This is
        # the check a broken restore fails; playing forward to the old position
        # does not satisfy it.
        "position_preserved": abs(drift) <= args.tolerance_seconds,
        "position_drift_seconds": round(drift, 3),
        "position_before_switch": round(before["position"], 3),
        "position_at_switch": round(after["at"], 3),
        "source_switched": source_switched,
        "playback_rate_preserved": abs(after["playbackRate"] - before["playbackRate"]) < 1e-6,
        "pause_state_preserved": bool(after["paused"]) == bool(before["paused"]),
        "captions_switched": after["captionsLanguage"] == (target.get("captionCode") or ""),
        "captions_language": after["captionsLanguage"],
        "language_switched": after["language"] == target.get("code"),
        "playback_advanced": (advanced.get("currentTime", 0) - after["at"]) >= seconds_played * 0.5,
        "advanced_seconds": round(advanced.get("currentTime", 0) - after["at"], 3),
    }


def verdict(checks: dict) -> bool:
    return all(
        checks[key]
        for key in ("position_preserved", "source_switched", "playback_rate_preserved",
                    "pause_state_preserved", "captions_switched", "language_switched",
                    "playback_advanced")
    )


def play_once(page, renditions, media_dir: Path, start: str, target_code: str, args) -> dict:
    """Serve one harness, load it, and return the measured switch."""
    harness_dir = build_harness(renditions, media_dir, start)
    httpd, base_url = serve(harness_dir, quiet=not args.verbose)
    try:
        page.goto(f"{base_url}/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)
        media = page.evaluate(
            """() => { const v = document.getElementById('demo-video');
                       return {error: v.error ? v.error.code : 0, readyState: v.readyState,
                               networkState: v.networkState}; }"""
        )
        if media["error"]:
            return {"harness": str(harness_dir), "media": media, "failed": True}
        started = measure(page)
        measured = run_switch(page, target_code, args)
    finally:
        httpd.shutdown()
    return {"harness": str(harness_dir), "media": media, "started": started,
            "measured": measured, "failed": False}


def run_manifest_mode(page, args) -> dict:
    from demo_manifest import load_manifest

    manifest = load_manifest(args.manifest)
    media_dir = args.media_dir or args.manifest.parent
    attempts = []
    for role in ("video", "raw"):
        renditions = video_files(manifest, media_dir, role)
        if len(renditions) < 2:
            continue
        start = args.language or renditions[0]["code"]
        target_code = args.switch_to or next(
            (rendition["code"] for rendition in renditions if rendition["code"] != start), ""
        )
        target = next((rendition for rendition in renditions if rendition["code"] == target_code), {})
        attempt = play_once(page, renditions, media_dir, start, target_code, args)
        attempt["role"] = role
        attempts.append(attempt)
        if attempt["failed"]:
            # The open-source Chromium build has no H.264 decoder; the recorded
            # webm carries the same timeline and captions, so the switch is still
            # verified rather than skipped.
            continue
        measured = attempt["measured"]
        checks = checks_from(measured, target, args, args.play_seconds)
        return {
            "mode": "manifest",
            "manifest": str(args.manifest),
            "media_dir": str(media_dir),
            "player_script": str(PLAYER_SCRIPT),
            "harness": attempt["harness"],
            "played_files": {rendition["code"]: rendition["src"] for rendition in renditions},
            "source_role": role,
            "duration_seconds": round(attempt["started"]["duration"], 3),
            "renditions": attempt["started"]["languages"],
            "switched": {"from": start, "to": target_code, "target_src": target.get("src", "")},
            "tolerance_seconds": args.tolerance_seconds,
            "playback": {"before": measured["before"], "after": measured["after"]},
            "checks": checks,
            "pass": verdict(checks),
        }
    if not attempts:
        return {
            "mode": "manifest",
            "pass": False,
            "reason": "the manifest has fewer than two playable renditions; "
                      "record both languages before verifying the switch",
        }
    return {
        "mode": "manifest",
        "pass": False,
        "reason": "chromium could not decode the recorded files",
        "attempts": [{"role": attempt["role"], "media": attempt["media"]} for attempt in attempts],
    }


def run_page_mode(page, args) -> dict:
    """Drive a deployed page: only claims a pass when that page has the switch."""
    page.goto(args.page_url, wait_until="domcontentloaded", timeout=60_000)
    present = page.evaluate(
        """() => {
            const video = document.getElementById('demo-video');
            if (!video) return {video: false, entries: [], deployed: false};
            const entries = JSON.parse(video.dataset.languages || '[]');
            return {video: true, entries: entries, deployed: entries.length > 1,
                    tracks: (video.textTracks || []).length};
        }"""
    )
    if not present["video"]:
        return {"mode": "page", "page_url": args.page_url, "pass": False,
                "reason": "#demo-video is not on the page"}
    if not present["deployed"]:
        return {
            "mode": "page",
            "page_url": args.page_url,
            "pass": False,
            "status": "not_deployed",
            "reason": "the page's player has no rendition list, so it cannot switch "
                      "language; run this again after the player change is deployed",
            "tracks": present["tracks"],
        }
    codes = [entry["code"] for entry in present["entries"]]
    start = args.language or codes[0]
    target_code = args.switch_to or next((code for code in codes if code != start), "")
    target = next((entry for entry in present["entries"] if entry["code"] == target_code), {})
    measured = run_switch(page, target_code, args)
    checks = checks_from(measured, target, args, args.play_seconds)
    return {
        "mode": "page",
        "page_url": args.page_url,
        "renditions": codes,
        "switched": {"from": start, "to": target_code, "target_src": target.get("src", "")},
        "tolerance_seconds": args.tolerance_seconds,
        "playback": {"before": measured["before"], "after": measured["after"]},
        "checks": checks,
        "pass": verdict(checks),
    }


def main() -> int:
    args = parse_args(sys.argv[1:])
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not args.headed,
            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            result = (run_manifest_mode(page, args) if args.manifest
                      else run_page_mode(page, args))
        finally:
            result_errors = errors
            context.close()
            browser.close()
    result["page_errors"] = result_errors
    if result_errors:
        result["pass"] = False
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
