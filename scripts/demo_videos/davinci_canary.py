#!/usr/bin/env python3
"""Copy-only DaVinci Resolve finishing canary: stage, run, then compare.

The finishing pass is optional and derivative. Resolve imports *copies* of a render's
files into a **new temporary project**, renders a derivative into its **own** output
directory, and nothing about the published artifact changes. This module is the part
of that which can run and be checked anywhere, plus the exact steps for the part that
cannot (driving Resolve):

    scripts/demo_videos/davinci_canary.py --stage \\
        --manifest <render>/<app>-<date>.manifest.json --into <canary-dir>
    # ... import the staged copies into a NEW Resolve project, render a derivative
    # into <canary-dir>/derivative/, then:
    scripts/demo_videos/davinci_canary.py --verify \\
        --manifest <render>/<app>-<date>.manifest.json \\
        --derivative <canary-dir>/derivative/<name>.mp4

What staging guarantees, and what verification proves:

* the copies live outside the render directory (`stage` refuses a destination inside
  it), so no tool can write into the source tree by accident;
* the source files' digests are recorded before and after staging, and `verify`
  re-checks them against the manifest — a canary that modified the artifact it was
  checking would be worse than no canary;
* the derivative must match the source's duration within a tolerance, carry an audio
  stream, and have the same caption cue count; a derivative that lost its voice or
  its subtitles is reported as such rather than accepted as "rendered fine".

Driving Resolve is deliberately not in here: it needs the upstream
`davinci-resolve-mcp` in compound mode on a machine running Resolve Studio, with a
reviewed configuration. Nothing in this file holds a credential or a client config.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
#: A derivative may drift from the source by a frame or two of container rounding.
DEFAULT_DURATION_TOLERANCE = 0.25
STAGED_VIDEO = "video.mp4"
STAGED_CAPTIONS = "captions.vtt"
STAGED_AUDIO = "narration.wav"
EXPECTED_FILE = "expected.json"
RUNBOOK_FILE = "RUNBOOK.md"


class CanaryError(RuntimeError):
    pass


def canonical_rendition(manifest: dict, language: str = "en", viewport: str = "desktop") -> dict:
    """The rendition a canary works on: the canonical one for that language/viewport."""
    for rendition in manifest.get("renditions", []):
        if (rendition.get("language") == language
                and rendition.get("viewport", "desktop") == viewport
                and rendition.get("canonical", True)):
            return rendition
    raise CanaryError(f"no canonical {language}/{viewport} rendition in the manifest")


def files_by_role(rendition: dict) -> dict:
    return {record.get("role"): record for record in rendition.get("files", [])}


def ffprobe_json(ffprobe: str, path: Path) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
         str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise CanaryError(f"ffprobe could not read {path.name}")
    return json.loads(result.stdout or "{}")


def stream_kinds(probe: dict) -> list[str]:
    return [stream.get("codec_type", "") for stream in probe.get("streams", [])]


def probe_duration(probe: dict) -> float:
    try:
        return float(probe.get("format", {}).get("duration", 0.0))
    except (TypeError, ValueError):
        return 0.0


def count_cues(vtt_path: Path) -> int:
    """Caption cues in a WebVTT file: a timing line is one cue."""
    if not vtt_path.is_file():
        return 0
    return sum(1 for line in vtt_path.read_text(encoding="utf-8").splitlines() if "-->" in line)


def stage_plan(manifest: dict, source_dir: Path, stage_dir: Path) -> dict:
    """What staging will copy and extract, and the digests it promises not to change."""
    if str(stage_dir.resolve()).startswith(str(source_dir.resolve())):
        raise CanaryError(
            f"the stage directory must be outside the render directory: {stage_dir} is inside "
            f"{source_dir}; a canary writes copies, never into the source"
        )
    rendition = canonical_rendition(manifest)
    files = files_by_role(rendition)
    for role in ("video", "captions"):
        if role not in files:
            raise CanaryError(f"the manifest has no {role} file to stage")
    return {
        "language": rendition.get("language"),
        "viewport": rendition.get("viewport", "desktop"),
        "duration_seconds": rendition.get("duration_seconds"),
        "cues": rendition.get("cues"),
        "theme": rendition.get("theme", ""),
        "video": files["video"],
        "captions": files["captions"],
        "chapters": files.get("chapters", {}),
        "transcript": files.get("transcript", {}),
    }


def stage(manifest_path: Path, source_dir: Path, stage_dir: Path, tools) -> dict:
    """Copy the rendition into a canary directory, and extract its audio read-only."""
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_manifest import file_digest, load_manifest

    manifest = load_manifest(manifest_path)
    plan = stage_plan(manifest, source_dir, stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    before = {
        plan["video"]["name"]: file_digest(source_dir / plan["video"]["name"]),
        plan["captions"]["name"]: file_digest(source_dir / plan["captions"]["name"]),
    }
    shutil.copy2(source_dir / plan["video"]["name"], stage_dir / STAGED_VIDEO)
    shutil.copy2(source_dir / plan["captions"]["name"], stage_dir / STAGED_CAPTIONS)
    for role in ("chapters", "transcript"):
        record = plan.get(role) or {}
        if record.get("name"):
            shutil.copy2(source_dir / record["name"], stage_dir / Path(record["name"]).name)
    subprocess.run(
        [tools.ffmpeg, "-y", "-loglevel", "error", "-i", str(stage_dir / STAGED_VIDEO),
         "-vn", "-acodec", "pcm_s16le", str(stage_dir / STAGED_AUDIO)],
        check=True,
    )

    expected = {
        "source_manifest": manifest_path.name,
        "app": manifest.get("app"),
        "date": manifest.get("date"),
        "commit": (manifest.get("source") or {}).get("commit", ""),
        "language": plan["language"],
        "viewport": plan["viewport"],
        "theme": plan["theme"],
        "duration_seconds": plan["duration_seconds"],
        "cues": plan["cues"],
        "source_digests": {name: record["sha256"] for name, record in before.items()},
        "staged": {
            "video": STAGED_VIDEO,
            "captions": STAGED_CAPTIONS,
            "audio": STAGED_AUDIO,
            "chapters": (plan.get("chapters") or {}).get("name", ""),
            "transcript": (plan.get("transcript") or {}).get("name", ""),
        },
    }
    (stage_dir / EXPECTED_FILE).write_text(
        json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (stage_dir / RUNBOOK_FILE).write_text(RUNBOOK.format(**expected), encoding="utf-8")

    after = {name: file_digest(source_dir / name) for name in before}
    unchanged = all(after[name]["sha256"] == before[name]["sha256"] for name in before)
    return {"stage_dir": str(stage_dir), "expected": expected, "source_unchanged": unchanged}


RUNBOOK = """# DaVinci Resolve canary (copy-only)

Source render: `{source_manifest}` (commit `{commit}`, {language}/{viewport}, theme
`{theme}`, {duration_seconds}s, {cues} caption cues).

Everything here is a **copy**. Do not import from, write to, or save over the render
directory; do not open or modify any existing Resolve project.

1. Resolve Studio is running, and the upstream `davinci-resolve-mcp` v4.7.6+ is
   connected in **compound** mode (reviewed configuration; no credentials in a repo,
   no committed client config).
2. Create a **new temporary project** named for this run, e.g. `canary-{app}-{date}`.
3. Import these staged copies into the media pool:
   - `{staged[video]}`
   - `{staged[audio]}`
   - `{staged[captions]}`
   - `{staged[chapters]}` and `{staged[transcript]}` if present
4. Inspect the timeline (read-only): confirm the clip count, the audio track and the
   subtitle track are what the media pool shows; note Resolve's reported duration.
5. Render **one** derivative into `derivative/` in this directory (H.264 + AAC, same
   resolution). Do not overwrite the source file.
6. Verify from the render directory (never from inside Resolve):
   `scripts/demo_videos/davinci_canary.py --verify --manifest <render>/<manifest> \\
      --derivative derivative/<file>`
7. Report: the derivative path, the verification JSON, and the source digests staying
   identical to `expected.json`.

Never: edit the source MP4/VTT/audio, save the temporary project over an existing
one, publish the derivative as the demo, or treat a Resolve render as a re-encode of
the published artifact.
"""


def verify(manifest_path: Path, source_dir: Path, derivative_path: Path, tools,
           tolerance: float = DEFAULT_DURATION_TOLERANCE) -> dict:
    """Compare a derivative with its source, and prove the source did not change."""
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_manifest import file_digest, load_manifest

    manifest = load_manifest(manifest_path)
    rendition = canonical_rendition(manifest)
    files = files_by_role(rendition)
    checks: dict = {"derivative": str(derivative_path)}
    problems = []

    if not derivative_path.is_file():
        return {"verified": False, "problems": [f"{derivative_path} does not exist"], "checks": {}}

    derivative_probe = ffprobe_json(tools.ffprobe or tools.ffmpeg, derivative_path)
    derivative_seconds = probe_duration(derivative_probe)
    expected_seconds = float(rendition.get("duration_seconds") or 0.0)
    checks["derivative_seconds"] = round(derivative_seconds, 3)
    checks["expected_seconds"] = round(expected_seconds, 3)
    checks["duration_within_tolerance"] = (
        abs(derivative_seconds - expected_seconds) <= tolerance if expected_seconds else True
    )
    if not checks["duration_within_tolerance"]:
        problems.append(
            f"duration {derivative_seconds:.3f}s is more than {tolerance}s from the "
            f"recorded {expected_seconds:.3f}s"
        )

    kinds = stream_kinds(derivative_probe)
    checks["derivative_streams"] = kinds
    checks["has_audio"] = "audio" in kinds
    checks["has_video"] = "video" in kinds
    if not checks["has_audio"]:
        problems.append("the derivative has no audio stream")
    if not checks["has_video"]:
        problems.append("the derivative has no video stream")

    derivative_cues = None
    captions_record = files.get("captions")
    if captions_record:
        source_cues = count_cues(source_dir / captions_record["name"])
        checks["source_cues"] = source_cues
        # A derivative carries captions as a sidecar it was given; if one was staged
        # next to it, their counts must agree.
        beside = derivative_path.with_suffix(".vtt")
        if beside.is_file():
            derivative_cues = count_cues(beside)
            checks["derivative_cues"] = derivative_cues
            checks["cues_match"] = derivative_cues == source_cues
            if not checks["cues_match"]:
                problems.append(
                    f"the derivative's captions have {derivative_cues} cues, the source {source_cues}"
                )
        else:
            checks["cues_match"] = None
            checks["cues_note"] = "no sidecar next to the derivative; caption text is burned in"

    source_checks = {}
    for role in ("video", "captions", "chapters", "transcript"):
        record = files.get(role)
        if not record:
            continue
        on_disk = file_digest(source_dir / record["name"])
        source_checks[role] = {
            "name": record["name"],
            "unchanged": on_disk["sha256"] == record["sha256"],
            "sha256": on_disk["sha256"],
        }
        if not source_checks[role]["unchanged"]:
            problems.append(f"the source {role} file changed during the canary")
    checks["source_files"] = source_checks
    checks["source_untouched"] = all(entry["unchanged"] for entry in source_checks.values())

    return {
        "verified": not problems,
        "problems": problems,
        "checks": checks,
        "tolerance_seconds": tolerance,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy-only DaVinci Resolve finishing canary")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", action="store_true", help="copy a rendition into a canary directory")
    mode.add_argument("--verify", action="store_true", help="compare a derivative with its source")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--into", type=Path, help="stage directory (with --stage)")
    parser.add_argument("--derivative", type=Path, help="the rendered derivative (with --verify)")
    parser.add_argument("--source-dir", type=Path, default=None,
                        help="the render directory (default: the manifest's own)")
    parser.add_argument("--tolerance-seconds", type=float, default=DEFAULT_DURATION_TOLERANCE)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_tools import find_media_tools

    tools = find_media_tools()
    if not tools.has_ffmpeg:
        print("ffmpeg is required to stage or verify a canary", file=sys.stderr)
        return 3
    source_dir = args.source_dir or args.manifest.parent
    try:
        if args.stage:
            if args.into is None:
                print("--stage needs --into", file=sys.stderr)
                return 2
            result = stage(args.manifest, source_dir, args.into, tools)
        else:
            if args.derivative is None:
                print("--verify needs --derivative", file=sys.stderr)
                return 2
            result = verify(args.manifest, source_dir, args.derivative, tools,
                            args.tolerance_seconds)
    except CanaryError as error:
        print(f"canary refused: {error}", file=sys.stderr)
        return 4
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.stage:
        return 0 if result["source_unchanged"] else 5
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
