#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The clip library: Draft on arrival, Approved only after a person watches.

The workflow this encodes, in the operator's words: one real development clip per visible
green slice, 30-90 seconds, separated by scenario; a render is added automatically as
**Draft** with its source commit, date and known defects; a human or the coordinator moves
it to **Approved** only after watching; a rejected clip is kept as history rather than
deleted; and nobody waits for a monolithic end-to-end journey before a clip can be added.

Two rules do the work:

* a clip is identified by the render it came from (scenario, date, manifest digest), so a
  re-render is a NEW clip and the rejected one stays visible as history beside it;
* ``approve`` refuses without a named watcher and a watched duration — an approval is a
  claim that somebody watched this artifact, and the library will not record a claim
  nobody made. ``register`` never approves anything, by construction.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CATALOG_SCHEMA = "scitex.demo-video.clip-catalog/1"
STATUSES = ("draft", "approved", "rejected")

# The clip budget the operator set for a single visible green slice.
MIN_CLIP_SECONDS = 30.0
MAX_CLIP_SECONDS = 90.0


class ClipError(RuntimeError):
    """A refusal: the caller asked for something the workflow does not allow."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_catalog(path: Path) -> dict:
    """The catalog, or an empty one. A malformed catalog starts empty rather than raising."""
    path = Path(path)
    if not path.exists():
        return {"schema": CATALOG_SCHEMA, "clips": []}
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": CATALOG_SCHEMA, "clips": []}
    if not isinstance(catalog, dict) or catalog.get("schema") != CATALOG_SCHEMA:
        raise ClipError("not a clip catalog")
    if not isinstance(catalog.get("clips"), list):
        catalog["clips"] = []
    return catalog


def save_catalog(path: Path, catalog: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def clip_id(manifest: dict, manifest_digest: str) -> str:
    """Scenario, date and render digest: a re-render is a new clip, not an edit."""
    app = manifest.get("app", "clip")
    date = manifest.get("date", "")
    return f"{app}-{date}-{manifest_digest[:8]}"


def rendition_facts(manifest: dict) -> tuple[list[str], list[str], dict]:
    """Languages, viewports and per-language duration from the manifest."""
    languages, viewports, durations = [], [], {}
    for rendition in manifest.get("renditions") or []:
        if not isinstance(rendition, dict):
            continue
        language = rendition.get("language", "")
        if language and language not in languages:
            languages.append(language)
        viewport = rendition.get("viewport", "")
        if viewport and viewport not in viewports:
            viewports.append(viewport)
        if language:
            durations[language] = rendition.get("duration_seconds")
    return sorted(languages), sorted(viewports), durations


def known_defects(manifest: dict, durations: dict) -> list[str]:
    """What the render itself says is wrong with it, plus the clip budget it misses."""
    defects = []
    environment = manifest.get("environment") or {}
    for language, reason in sorted((environment.get("narration_failures") or {}).items()):
        defects.append(f"narration failed for {language}: {reason}")
    if not environment.get("voice"):
        defects.append("recorded without voice narration")
    theme = environment.get("theme") or manifest.get("theme") or ""
    verified = environment.get("theme_verified", manifest.get("theme_verified"))
    if verified is False:
        # The theme name is not required to report this: a render that was asked for a
        # theme and did not verify it is defective whether or not it recorded the name.
        # Reported without it, the rejected take looked defect-free, which is exactly the
        # entry a reader needs to understand.
        defects.append(
            f"theme {theme} was requested and not verified on every surface" if theme
            else "the requested theme was not verified on every surface"
        )
    if manifest.get("theme_verified") is False and isinstance(manifest.get("theme_map"), dict):
        dark = sorted(name for name, state in manifest["theme_map"].items()
                      if isinstance(state, dict) and state.get("background_theme") == "dark")
        if dark:
            defects.append("dark surfaces remained: " + ", ".join(dark))
    for language, seconds in sorted(durations.items()):
        if not isinstance(seconds, (int, float)):
            defects.append(f"{language}: no recorded duration")
            continue
        if seconds < MIN_CLIP_SECONDS:
            defects.append(f"{language}: {seconds:.1f}s is shorter than the 30s clip budget")
        elif seconds > MAX_CLIP_SECONDS:
            defects.append(f"{language}: {seconds:.1f}s is longer than the 90s clip budget")
    return defects


def register(catalog_path: Path, manifest_path: Path, *, queue_item: str = "") -> dict:
    """Add a render to the catalog as Draft. Never approves, never overwrites a status.

    An existing clip with the same identity is left exactly as it is: watching it again
    is not this function's business, and a Draft that arrives twice is still a Draft.
    """
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = sha256_file(manifest_path)
    catalog = load_catalog(catalog_path)
    identifier = clip_id(manifest, digest)

    for clip in catalog["clips"]:
        if clip.get("id") == identifier:
            clip["seen_again_at"] = now()
            save_catalog(catalog_path, catalog)
            return clip

    languages, viewports, durations = rendition_facts(manifest)
    source = manifest.get("source") or {}
    clip = {
        "id": identifier,
        "status": "draft",                 # every arrival starts here; only a person moves it
        "scenario": manifest.get("app", ""),
        "queue_item": queue_item,
        "title": (manifest.get("titles") or {}),
        "date": manifest.get("date", ""),
        "registered_at": now(),
        "captured_at": manifest.get("generated_at", ""),
        "dev_commit": source.get("commit", ""),
        "dev_branch": source.get("branch", ""),
        "dev_dirty": source.get("dirty"),
        "languages": languages,
        "viewports": viewports,
        "durations": durations,
        "manifest": str(manifest_path),
        "manifest_sha256": digest,
        "defects": known_defects(manifest, durations),
        "watch": None,
        "history": [{"at": now(), "what": "registered as draft", "by": "pipeline"}],
    }
    catalog["clips"].append(clip)
    save_catalog(catalog_path, catalog)
    return clip


def find(catalog: dict, identifier: str) -> dict:
    for clip in catalog["clips"]:
        if clip.get("id") == identifier:
            return clip
    raise ClipError(f"no clip {identifier!r} in the catalog")


def approve(catalog_path: Path, identifier: str, *, by: str, watched_seconds: float,
            notes: str = "") -> dict:
    """Draft -> Approved, and only with a named watcher and a watched duration."""
    if not by or not str(by).strip():
        raise ClipError("an approval needs a named watcher")
    if not isinstance(watched_seconds, (int, float)) or watched_seconds <= 0:
        raise ClipError("an approval needs a watched duration: somebody watched this")
    catalog = load_catalog(catalog_path)
    clip = find(catalog, identifier)
    if clip.get("status") == "rejected":
        raise ClipError("a rejected clip is history; record a new render instead")
    clip["status"] = "approved"
    clip["watch"] = {"by": str(by).strip(), "watched_seconds": float(watched_seconds),
                     "at": now(), "notes": notes}
    clip["history"].append({"at": now(), "what": "approved after a watch", "by": by})
    save_catalog(catalog_path, catalog)
    return clip


def reject(catalog_path: Path, identifier: str, *, by: str, reason: str) -> dict:
    """Kept, not deleted: a rejected clip stays in the catalog as history."""
    if not by or not str(by).strip():
        raise ClipError("a rejection needs a named person")
    if not reason or not str(reason).strip():
        raise ClipError("a rejection needs a reason")
    catalog = load_catalog(catalog_path)
    clip = find(catalog, identifier)
    clip["status"] = "rejected"
    clip["rejection"] = {"by": str(by).strip(), "reason": str(reason).strip(), "at": now()}
    clip["history"].append({"at": now(), "what": f"rejected: {reason}", "by": by})
    save_catalog(catalog_path, catalog)
    return clip


def summary(catalog: dict) -> dict:
    """Counts by status, plus what is waiting on a person rather than on the pipeline."""
    counts = dict.fromkeys(STATUSES, 0)
    for clip in catalog["clips"]:
        counts[clip.get("status", "draft")] = counts.get(clip.get("status", "draft"), 0) + 1
    drafts_with_defects = [
        clip["id"] for clip in catalog["clips"]
        if clip.get("status") == "draft" and clip.get("defects")
    ]
    return {
        "clips": len(catalog["clips"]),
        "by_status": counts,
        "drafts_with_defects": drafts_with_defects,
        "awaiting_a_watch": counts.get("draft", 0),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True)
    action = parser.add_subparsers(dest="action", required=True)

    add = action.add_parser("register")
    add.add_argument("--manifest", required=True)
    add.add_argument("--queue-item", default="")

    yes = action.add_parser("approve")
    yes.add_argument("--clip", required=True)
    yes.add_argument("--by", required=True)
    yes.add_argument("--watched-seconds", type=float, required=True)
    yes.add_argument("--notes", default="")

    no = action.add_parser("reject")
    no.add_argument("--clip", required=True)
    no.add_argument("--by", required=True)
    no.add_argument("--reason", required=True)

    action.add_parser("summary")

    args = parser.parse_args()
    try:
        if args.action == "register":
            clip = register(args.catalog, args.manifest, queue_item=args.queue_item)
            print(json.dumps({"id": clip["id"], "status": clip["status"],
                              "defects": clip["defects"]}, indent=2))
        elif args.action == "approve":
            clip = approve(args.catalog, args.clip, by=args.by,
                           watched_seconds=args.watched_seconds, notes=args.notes)
            print(json.dumps({"id": clip["id"], "status": clip["status"]}, indent=2))
        elif args.action == "reject":
            clip = reject(args.catalog, args.clip, by=args.by, reason=args.reason)
            print(json.dumps({"id": clip["id"], "status": clip["status"]}, indent=2))
        else:
            print(json.dumps(summary(load_catalog(args.catalog)), indent=2))
    except ClipError as error:
        print(f"refused: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
