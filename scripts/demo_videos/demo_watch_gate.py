"""The human watch gate: publishing a bilingual video needs both languages watched.

docs/ops/demo-videos.md already says "Watch both languages", and the spec
(docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md section 11) makes it a delivery gate.
Until now that instruction lived only in prose, so a video could be copied to the
media volume with only the English one watched — the Japanese rendition is the
one that silently breaks (untranslated pages, wrapped captions, manga-length
text), and it is the one nobody on the team reads by default.

This module makes the gate a file and a command:

* ``init``     writes ``<app>-<date>.watch-gate.json`` next to the render, listing
               every language the manifest requires, all unrecorded;
* ``record``   records one human's watch of one language, bound to the artifact's
               sha256 and the source commit, so a re-render invalidates it;
* ``status``   is the publish check: exit 1 until both languages are watched with
               a passing verdict against the artifacts currently on disk.

The gate cannot be satisfied by the pipeline itself: a video is watched by a
person, and this file is the evidence that a person did.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

from demo_manifest import MANIFEST_SCHEMA, WATCH_GATE_SCHEMA, file_digest, load_manifest

VERDICTS = ("pass", "fail")
# A watch shorter than this cannot have seen a one-minute tutorial; the renderer
# still writes the entry, but `status` refuses to call a too-short watch a gate.
MINIMUM_WATCHED_SECONDS = 5.0


def gate_path(out_dir: Path, app: str, date: str) -> Path:
    return Path(out_dir) / f"{app}-{date}.watch-gate.json"


def init_gate(manifest: dict, languages=None, path: Path | None = None) -> dict:
    """A gate listing every language the manifest requires, none recorded yet."""
    languages = list(languages or manifest.get("matrix", {}).get("languages", []))
    renditions = {}
    for rendition in manifest.get("renditions", []):
        language = rendition.get("language")
        if language not in languages:
            continue
        artifact = record_for(rendition)
        if artifact.get("name"):
            renditions[language] = artifact
    gate = {
        "schema": WATCH_GATE_SCHEMA,
        "manifest_schema": manifest.get("schema", MANIFEST_SCHEMA),
        "app": manifest.get("app"),
        "date": manifest.get("date"),
        "commit": (manifest.get("source") or {}).get("commit", ""),
        "required_languages": languages,
        "watches": dict.fromkeys(languages),
        "artifacts": renditions,
    }
    if path is not None:
        save_gate(path, gate)
    return gate


def record_for(rendition: dict) -> dict:
    """The artifact a watch is about: the video, identified by digest."""
    for record in rendition.get("files", []):
        if record.get("role") == "video":
            return {"name": record.get("name"), "sha256": record.get("sha256"),
                    "bytes": record.get("bytes"), "duration_seconds": rendition.get("duration_seconds")}
    return {}


def save_gate(path: Path, gate: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_gate(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_watch(gate: dict, *, language: str, watched_by: str, verdict: str,
                 watched_seconds: float, notes: str = "",
                 watched_at: str = "") -> dict:
    """Add one human's verdict for one language to the gate."""
    if language not in gate.get("required_languages", []):
        raise ValueError(f"{language} is not a required language of this gate")
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if not watched_by.strip():
        raise ValueError("the gate records who watched the video")
    artifact = gate.get("artifacts", {}).get(language, {})
    gate["watches"][language] = {
        "watched_by": watched_by.strip(),
        "watched_at": watched_at or datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "verdict": verdict,
        "watched_seconds": float(watched_seconds),
        "notes": notes.strip(),
        "commit": gate.get("commit", ""),
        "artifact": artifact.get("name", ""),
        "artifact_sha256": artifact.get("sha256", ""),
    }
    return gate


def gate_status(gate: dict, out_dir: Path | None = None) -> dict:
    """Publish check: is every required language watched, passing, and current?"""
    required = list(gate.get("required_languages", []))
    watched, missing, failing, stale = [], [], [], []
    for language in required:
        entry = (gate.get("watches") or {}).get(language)
        if not entry:
            missing.append(language)
            continue
        watched.append(language)
        if entry.get("verdict") != "pass":
            failing.append({"language": language, "verdict": entry.get("verdict")})
        elif float(entry.get("watched_seconds", 0)) < MINIMUM_WATCHED_SECONDS:
            failing.append({"language": language, "verdict": "too-short",
                            "watched_seconds": entry.get("watched_seconds")})
        drift = artifact_drift(gate, language, out_dir, entry)
        if drift:
            stale.append({"language": language, "reason": drift})
    return {
        "app": gate.get("app"),
        "date": gate.get("date"),
        "required": required,
        "watched": watched,
        "missing": missing,
        "failing": failing,
        "stale": stale,
        "publishable": bool(required) and not missing and not failing and not stale,
    }


def artifact_drift(gate: dict, language: str, out_dir: Path | None, entry: dict) -> str:
    """Why this watch no longer covers the file: re-render, or a changed artifact."""
    artifact = (gate.get("artifacts") or {}).get(language) or {}
    if artifact.get("sha256") and entry.get("artifact_sha256") != artifact.get("sha256"):
        return "the video was re-rendered after the watch"
    if out_dir and artifact.get("name"):
        on_disk = file_digest(Path(out_dir) / artifact["name"])
        if on_disk.get("missing"):
            return "the watched file is gone"
        if on_disk.get("sha256") != artifact.get("sha256"):
            return "the file on disk differs from the watched artifact"
    return ""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Human watch gate for demo videos")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create an unwatched gate from a manifest")
    init_parser.add_argument("manifest", type=Path)
    init_parser.add_argument("--out-dir", type=Path, default=None,
                             help="where the gate file is written (default: next to the manifest)")

    record_parser = subparsers.add_parser("record", help="record one human watch")
    record_parser.add_argument("gate", type=Path)
    record_parser.add_argument("--language", required=True)
    record_parser.add_argument("--by", required=True, dest="watched_by")
    record_parser.add_argument("--verdict", default="pass", choices=VERDICTS)
    record_parser.add_argument("--watched-seconds", type=float, default=0.0)
    record_parser.add_argument("--notes", default="")

    status_parser = subparsers.add_parser("status", help="publish check for one gate")
    status_parser.add_argument("gate", type=Path)
    status_parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "init":
        manifest = load_manifest(args.manifest)
        path = (args.out_dir or args.manifest.parent) / gate_path(
            Path("."), manifest.get("app", ""), manifest.get("date", "")
        ).name
        gate = init_gate(manifest, path=path)
        print(f"wrote {path} ({len(gate['required_languages'])} languages to watch)")
        return 0
    if args.command == "record":
        gate = load_gate(args.gate)
        record_watch(gate, language=args.language, watched_by=args.watched_by,
                     verdict=args.verdict, watched_seconds=args.watched_seconds,
                     notes=args.notes)
        save_gate(args.gate, gate)
        status = gate_status(gate, args.out_dir)
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    gate = load_gate(args.gate)
    status = gate_status(gate, args.out_dir)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status["publishable"] else 1


if __name__ == "__main__":
    sys.exit(main())
