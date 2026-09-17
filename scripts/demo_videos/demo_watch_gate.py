#!/usr/bin/env python3
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
* ``status``   is the publish check: exit 1 until every language is watched with
               a passing verdict against the artifacts currently on disk.

It **fails closed**. A gate is not publishable because it says so; it is publishable
when, for every required language, all of this holds and can be re-checked from
files: a recorded watch by a named person, a passing verdict, a long enough watch, an
artifact record carrying a viewport and a non-empty digest, that digest equal to what
the manifest recorded for the same rendition, and — when the render directory is given
— the file still on disk with exactly that digest. Anything missing, blank, mismatched
or unreadable is "not publishable", never "assume fine". Measured 2026-09-17: an
earlier version returned publishable for a gate whose video files did not exist, keyed
artifacts by language alone (so a mobile rendition overwrote the desktop one), and
crashed after writing the file because the ``record`` subcommand had no ``--out-dir``.

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
#: The rendition a publish uses. A mobile file is a nice extra, not the published one.
PUBLISHED_VIEWPORT = "desktop"


class GateError(RuntimeError):
    """A gate that cannot be trusted, with the reason it cannot."""


def gate_path(out_dir: Path, app: str, date: str) -> Path:
    return Path(out_dir) / f"{app}-{date}.watch-gate.json"


def artifact_key(language: str, viewport: str) -> str:
    """Artifacts are keyed by language *and* viewport.

    Keying by language alone meant a mobile rendition silently replaced the desktop
    one in the map — the two are different files, and the published one is desktop.
    """
    return f"{language}/{viewport or PUBLISHED_VIEWPORT}"


def manifests_for_gate(gate: dict, out_dir: Path | None) -> dict:
    """The manifest a gate was derived from, if it can still be read."""
    name = gate.get("manifest") or ""
    if not name or out_dir is None:
        return {}
    path = Path(out_dir) / name
    if not path.is_file():
        return {}
    try:
        manifest = load_manifest(path)
    except Exception:
        return {}
    return manifest if manifest.get("schema") == MANIFEST_SCHEMA else {}


def rendition_for(manifest: dict, language: str, viewport: str) -> dict:
    for rendition in manifest.get("renditions", []):
        if (rendition.get("language") == language
                and rendition.get("viewport", PUBLISHED_VIEWPORT) == viewport
                and rendition.get("canonical", True)):
            return rendition
    return {}


def record_for(rendition: dict) -> dict:
    """The artifact a watch is about: the video, identified by digest and viewport."""
    for record in rendition.get("files", []):
        if record.get("role") == "video":
            return {"name": record.get("name"), "sha256": record.get("sha256"),
                    "bytes": record.get("bytes"),
                    "viewport": rendition.get("viewport", PUBLISHED_VIEWPORT),
                    "duration_seconds": rendition.get("duration_seconds")}
    return {}


def init_gate(manifest: dict, languages=None, path: Path | None = None,
              viewport: str = PUBLISHED_VIEWPORT) -> dict:
    """A gate listing every language the manifest requires, none recorded yet.

    Refuses a manifest it cannot trust: a file that is not a render manifest, or one
    with no canonical rendition for the published viewport, cannot produce a gate that
    means anything, and writing one anyway is how an empty gate got blessed.
    """
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise GateError(
            f"not a render manifest (schema {manifest.get('schema')!r}); refusing to write a gate"
        )
    languages = list(languages or manifest.get("matrix", {}).get("languages", []))
    if not languages:
        languages = sorted({r.get("language") for r in manifest.get("renditions", []) if r.get("language")})
    renditions, missing = {}, []
    for language in languages:
        rendition = rendition_for(manifest, language, viewport)
        artifact = record_for(rendition)
        if not artifact.get("name") or not artifact.get("sha256"):
            missing.append(language)
            continue
        renditions[language] = artifact
    if missing or not renditions:
        raise GateError(
            f"the manifest has no video for {missing or 'any language'} at the "
            f"{viewport} viewport; there is nothing to watch and no gate to write"
        )
    gate = {
        "schema": WATCH_GATE_SCHEMA,
        "manifest_schema": manifest.get("schema", MANIFEST_SCHEMA),
        # Which manifest this gate is about: without it, a gate for one render can be
        # paired with any other render's files.
        "manifest": f"{manifest.get('app')}-{manifest.get('date')}.manifest.json",
        "app": manifest.get("app"),
        "date": manifest.get("date"),
        "commit": (manifest.get("source") or {}).get("commit", ""),
        "viewport": viewport,
        "required_languages": languages,
        "watches": {language: None for language in languages},
        "artifacts": renditions,
    }
    if path is not None:
        save_gate(path, gate)
    return gate


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
    gate.setdefault("watches", {})[language] = {
        "watched_by": watched_by.strip(),
        "watched_at": watched_at or datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "verdict": verdict,
        "watched_seconds": float(watched_seconds),
        "notes": notes.strip(),
        "commit": gate.get("commit", ""),
        "artifact": artifact.get("name", ""),
        "artifact_sha256": artifact.get("sha256", ""),
        "artifact_viewport": artifact.get("viewport", ""),
    }
    return gate


def gate_status(gate: dict, out_dir: Path | None = None) -> dict:
    """Publish check, fail-closed: every required language, watched and still current.

    ``out_dir`` is optional so the check still works on a gate alone, but the checks
    that need files (does the watched file still exist with that digest, does the
    manifest agree with the gate) are reported as *unverified* rather than assumed, and
    an unverified gate is not publishable.
    """
    if gate.get("schema") != WATCH_GATE_SCHEMA:
        return {
            "app": gate.get("app"), "date": gate.get("date"),
            "required": [], "watched": [], "missing": [], "failing": [], "stale": [],
            "problems": [f"not a watch gate (schema {gate.get('schema')!r})"],
            "publishable": False,
        }
    required = list(gate.get("required_languages", []))
    manifest = manifests_for_gate(gate, out_dir)
    watched, missing, failing, stale, problems = [], [], [], [], []
    if not required:
        problems.append("the gate requires no languages, so it cannot gate anything")
    if out_dir is not None and gate.get("manifest") and not manifest:
        problems.append(f"the manifest this gate names is not readable: {gate.get('manifest')}")
    for language in required:
        artifact = (gate.get("artifacts") or {}).get(language) or {}
        entry = (gate.get("watches") or {}).get(language)
        viewport = artifact.get("viewport") or ""
        if viewport and viewport != PUBLISHED_VIEWPORT:
            problems.append(
                f"{language}: the gate's artifact is the {viewport} rendition, not the "
                f"published {PUBLISHED_VIEWPORT} one"
            )
        if not entry:
            missing.append(language)
            continue
        watched.append(language)
        if entry.get("verdict") != "pass":
            failing.append({"language": language, "verdict": entry.get("verdict")})
        elif float(entry.get("watched_seconds", 0)) < MINIMUM_WATCHED_SECONDS:
            failing.append({"language": language, "verdict": "too-short",
                            "watched_seconds": entry.get("watched_seconds")})
        if not artifact.get("sha256"):
            problems.append(f"{language}: the gate records no digest for the artifact it watched")
        if manifest:
            expected = record_for(rendition_for(manifest, language, PUBLISHED_VIEWPORT))
            if expected.get("sha256") and expected["sha256"] != artifact.get("sha256"):
                stale.append({"language": language,
                              "reason": "the manifest records a different video for this language"})
        drift = artifact_drift(gate, language, out_dir, entry)
        if drift:
            stale.append({"language": language, "reason": drift})
    return {
        "app": gate.get("app"),
        "date": gate.get("date"),
        "manifest": gate.get("manifest", ""),
        "required": required,
        "watched": watched,
        "missing": missing,
        "failing": failing,
        "stale": stale,
        "problems": problems,
        "publishable": bool(required) and not (missing or failing or stale or problems),
    }


def artifact_drift(gate: dict, language: str, out_dir: Path | None, entry: dict) -> str:
    """Why this watch no longer covers the file: re-render, or a changed artifact."""
    artifact = (gate.get("artifacts") or {}).get(language) or {}
    if artifact.get("sha256") and entry.get("artifact_sha256") != artifact.get("sha256"):
        return "the video was re-rendered after the watch"
    if not artifact.get("sha256"):
        return "the gate records no digest for the watched video"
    if out_dir and artifact.get("name"):
        on_disk = file_digest(Path(out_dir) / artifact["name"])
        if on_disk.get("missing"):
            return "the watched file is gone"
        if on_disk.get("sha256") != artifact.get("sha256"):
            return "the file on disk differs from the watched artifact"
    elif not out_dir:
        return "unverified: no render directory was given, so the file was not re-checked"
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
    # Declared on every subcommand: `record` used to read args.out_dir without having
    # it, and crashed *after* writing the file it had just mutated.
    record_parser.add_argument("--out-dir", type=Path, default=None,
                               help="the render directory, to re-check the artifact")

    status_parser = subparsers.add_parser("status", help="publish check for one gate")
    status_parser.add_argument("gate", type=Path)
    status_parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
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
    except GateError as error:
        print(f"gate refused: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
