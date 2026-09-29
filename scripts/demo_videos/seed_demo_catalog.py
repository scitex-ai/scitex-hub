#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed the demo catalog from renders that already exist on disk.

The staff index is only useful if it shows the real artifacts the team already has, and
seeding it by hand in a shell is how an index drifts from reality. This is the one command
that does it, and it is idempotent: a render already registered is reported as seen again,
not duplicated.

It never approves anything. A take that a person has judged unusable is registered and
then explicitly rejected with a reason, so the rejection is visible as history with its
cause attached rather than the entry quietly disappearing.

    python scripts/demo_videos/seed_demo_catalog.py \
        --catalog /scratch/internal-demos/demos-catalog.json \
        --render projects=/scratch/beta-video-projects-20260917 \
        --reject projects=/scratch/beta-video-projects-light-en-brian-20260917 \
               --reason "not a light-mode artifact: the workspace and Create stay dark"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "infra" / "public_app"))

import clip_registry  # noqa: E402


def manifest_for(directory: Path, app: str) -> Path:
    """The newest manifest for an app in a render directory."""
    candidates = sorted(directory.glob(f"{app}-*.manifest.json"))
    if not candidates:
        candidates = sorted(directory.glob("*.manifest.json"))
    if not candidates:
        raise SystemExit(f"no manifest for {app!r} in {directory}")
    return candidates[0]


def seed(catalog: Path, renders: list[tuple[str, Path, str]], rejects: dict[str, str],
         approved: dict[str, dict]) -> list[dict]:
    """Register every render, then apply the state a person decided, explicitly."""
    registered = []
    for app, directory, queue_item in renders:
        clip = clip_registry.register(catalog, manifest_for(Path(directory), app),
                                      queue_item=queue_item)
        registered.append(clip)
        print(f"registered {app}: {clip['id']} status={clip['status']}")
        for defect in clip["defects"]:
            print(f"    defect: {defect}")

    for app, directory, queue_item in renders:
        key = str(Path(directory))
        if key in rejects:
            clip = clip_registry.load_catalog(catalog)
            match = next((c for c in clip["clips"]
                          if c["manifest"] == str(manifest_for(Path(directory), app))), None)
            if match and match.get("status") != "rejected":
                clip_registry.reject(catalog, match["id"], by="operator",
                                     reason=rejects[key])
                print(f"rejected {app}: {match['id']}")
        if key in approved:
            who = approved[key]
            clip = clip_registry.load_catalog(catalog)
            match = next((c for c in clip["clips"]
                          if c["manifest"] == str(manifest_for(Path(directory), app))), None)
            if match and match.get("status") == "draft":
                clip_registry.approve(catalog, match["id"], by=who["by"],
                                      watched_seconds=who["watched_seconds"])
                print(f"approved {app}: {match['id']}")
    return registered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--render", action="append", default=[],
                        help="APP=DIR, repeatable; registers as Draft")
    parser.add_argument("--reject", action="append", default=[],
                        help="APP=DIR to mark Rejected (history, with --reason)")
    parser.add_argument("--reason", default="")
    parser.add_argument("--queue-item", default="")
    args = parser.parse_args()

    renders = []
    for item in args.render + args.reject:
        app, _, directory = item.partition("=")
        renders.append((app, Path(directory), args.queue_item))

    rejects = {}
    if args.reject:
        if not args.reason.strip():
            print("refused: marking a take Rejected needs a --reason", file=sys.stderr)
            return 1
        for item in args.reject:
            app, _, directory = item.partition("=")
            rejects[str(Path(directory))] = args.reason

    catalog = Path(args.catalog)
    seed(catalog, renders, rejects, {})
    print(json.dumps(clip_registry.summary(clip_registry.load_catalog(catalog)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
