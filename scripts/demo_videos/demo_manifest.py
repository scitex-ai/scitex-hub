"""Reproducible metadata for a demo-video render.

A published video is only useful if someone can say what it was recorded from.
The manifest next to the rendered files records:

* the scenario and its digest, so a caption change is visible as a different input;
* the commit, branch and dirty state of the checkout that produced it, so the
  tutorial is versioned against the Hub release (spec section 8);
* the toolchain (python, playwright/chromium, ffmpeg/ffprobe, narration backend,
  caption font), because "same scenario, different voice engine" is a different
  video;
* the UI-contract fingerprint, so a control that moves marks the video stale;
* per-artifact sha256, size and duration, so the files on the media volume can be
  checked against what was recorded instead of trusted.

`verify_manifest` reads a manifest back and compares it with the files on disk;
that is the playback-independent half of the publish check.
"""

import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path

MANIFEST_SCHEMA = "scitex.demo-video.manifest/1"
WATCH_GATE_SCHEMA = "scitex.demo-video.watch-gate/1"
MAX_LISTED_DIRTY_FILES = 20


def file_digest(path: Path) -> dict:
    """Size and sha256 of one artifact, or an explicit absence."""
    path = Path(path)
    if not path.exists():
        return {"name": path.name, "bytes": 0, "sha256": "", "missing": True}
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "missing": False,
    }


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def git_state(repo_root: Path) -> dict:
    """What the render was made from: the release-versioning input."""
    repo_root = Path(repo_root)
    dirty_lines = [line for line in _git(repo_root, "status", "--porcelain").splitlines() if line]
    return {
        "branch": _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git(repo_root, "rev-parse", "HEAD"),
        "commit_date": _git(repo_root, "show", "-s", "--format=%cI", "HEAD"),
        "dirty": bool(dirty_lines),
        "dirty_files": [line.split(maxsplit=1)[-1] for line in dirty_lines[:MAX_LISTED_DIRTY_FILES]],
        "dirty_file_count": len(dirty_lines),
    }


def toolchain(tools=None, narration_backend: str = "", voice: bool = False,
              caption_font: str = "", font_available: bool | None = None,
              narration_failures: dict | None = None) -> dict:
    """The tool versions a render used; the media binaries come from demo_tools."""
    playwright_version = ""
    try:
        from importlib.metadata import version

        playwright_version = version("playwright")
    except Exception:
        playwright_version = ""
    info = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "playwright": playwright_version,
        "platform": platform.platform(),
        "narration_backend": narration_backend,
        # Whether a voice track made it into the render, and why not when it did
        # not: a manifest that claims narration over a silent file is worse than
        # one that admits the TTS backend was unreachable.
        "voice": bool(voice),
        "narration_failures": dict(narration_failures or {}),
        "caption_font": caption_font,
        "caption_font_available": font_available,
    }
    if tools is not None:
        from demo_tools import encoder_support, ffmpeg_version, ffprobe_version

        info.update(
            {
                "ffmpeg_path": tools.ffmpeg,
                "ffmpeg_source": tools.source,
                "ffmpeg_version": ffmpeg_version(tools.ffmpeg),
                "ffmpeg_encoders": encoder_support(tools.ffmpeg),
                "ffprobe_path": tools.ffprobe,
                "ffprobe_version": ffprobe_version(tools.ffprobe),
            }
        )
    return info


def build_manifest(*, app: str, date: str, titles: dict, scenario_path: Path,
                   repo_root: Path, base_url: str, renditions: list[dict],
                   tools_info: dict, contracts: dict, viewports: list[str],
                   languages: list[str], steps: int = 0, generated_at: str = "") -> dict:
    """Assemble the manifest; ``renditions`` carry the per-artifact digests."""
    scenario_text = Path(scenario_path).read_text(encoding="utf-8")
    return {
        "schema": MANIFEST_SCHEMA,
        "app": app,
        "date": date,
        "titles": titles,
        "generated_at": generated_at or datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        "scenario": {
            "path": str(Path(scenario_path).name),
            "sha256": text_digest(scenario_text),
            "bytes": len(scenario_text.encode("utf-8")),
            "steps": steps,
        },
        "source": git_state(repo_root),
        "environment": {"base_url": base_url, **tools_info},
        "ui_contract": contracts,
        "matrix": {"viewports": viewports, "languages": languages},
        "renditions": renditions,
        "watch_gate": {
            "schema": WATCH_GATE_SCHEMA,
            "required_languages": languages,
            "status": "pending",
        },
    }


def write_manifest(path: Path, manifest: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest_path(out_dir: Path, app: str, date: str) -> Path:
    return Path(out_dir) / f"{app}-{date}.manifest.json"


def recorded_artifacts(manifest: dict, language: str, viewport: str = "desktop",
                       ui_locale: str = "") -> list[dict]:
    """Artifacts of one rendition; ``ui_locale`` disambiguates alternates."""
    for rendition in manifest.get("renditions", []):
        if rendition.get("language") != language or rendition.get("viewport") != viewport:
            continue
        if ui_locale and rendition.get("ui_locale", rendition.get("locale")) != ui_locale:
            continue
        return list(rendition.get("files", []))
    return []


def verify_manifest(manifest: dict, out_dir: Path) -> dict:
    """Compare the manifest with the files next to it; report every mismatch."""
    out_dir = Path(out_dir)
    checked, mismatches = 0, []
    for rendition in manifest.get("renditions", []):
        for record in rendition.get("files", []):
            if record.get("missing"):
                continue
            checked += 1
            on_disk = file_digest(out_dir / record["name"])
            if on_disk["missing"]:
                mismatches.append({"name": record["name"], "reason": "file is gone"})
            elif on_disk["sha256"] != record.get("sha256") or on_disk["bytes"] != record.get("bytes"):
                mismatches.append(
                    {
                        "name": record["name"],
                        "reason": "digest differs from the manifest",
                        "manifest_bytes": record.get("bytes"),
                        "disk_bytes": on_disk["bytes"],
                    }
                )
    return {
        "checked": checked,
        "mismatches": mismatches,
        "verified": checked > 0 and not mismatches,
        "out_dir": str(out_dir),
    }


def summarize(manifest: dict) -> dict:
    """A short, printable view for the render log."""
    renditions = []
    for rendition in manifest.get("renditions", []):
        renditions.append(
            {
                "language": rendition.get("language"),
                "ui_locale": rendition.get("ui_locale", rendition.get("locale")),
                "viewport": rendition.get("viewport"),
                "canonical": rendition.get("canonical", True),
                "seconds": rendition.get("duration_seconds"),
                "files": [record["name"] for record in rendition.get("files", [])],
            }
        )
    return {
        "schema": manifest.get("schema"),
        "app": manifest.get("app"),
        "date": manifest.get("date"),
        "commit": (manifest.get("source") or {}).get("commit", "")[:12],
        "dirty": (manifest.get("source") or {}).get("dirty"),
        "renditions": renditions,
    }


def short_commit(manifest: dict) -> str:
    return (manifest.get("source") or {}).get("commit", "")[:12]


def find_manifest(out_dir: Path, app: str, date: str = "") -> Path | None:
    """The manifest for an app in an output directory (any date when unspecified)."""
    out_dir = Path(out_dir)
    pattern = f"{app}-{date}.manifest.json" if date else f"{app}-*.manifest.json"
    matches = sorted(out_dir.glob(pattern))
    return matches[-1] if matches else None
