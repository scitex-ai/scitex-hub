#!/usr/bin/env python3
"""Promotion metadata: what a reviewed render becomes when Docs embeds it.

A manifest is render-time evidence (what was recorded, from which commit, with
which digests). A promotion file is an authoring decision: which of those files
may be embedded, under which title, next to which docs page, pinned to which
digests so nothing is re-encoded or silently swapped later.

The split matters because they change for different reasons. Re-rendering rewrites
the manifest and invalidates a watch; promoting rewrites this file and does not
touch a byte of media. docs/ops/demo-videos.md has the promotion step.

    scripts/demo_videos/promote.py --manifest <render>/<app>-<date>.manifest.json \\
        --by <operator> --docs-page /apps/docs/#howto-projects \\
        --embed-key guide-create-first-project
"""

import argparse
import datetime
import json
import sys
import tomllib
from pathlib import Path

PROMOTION_SCHEMA = "scitex.demo-video.promotion/1"
# The roles a promoted asset can carry, and the manifest role each comes from.
PROMOTED_ROLES = {
    "video": "video",
    "captions": "captions",
    "chapters": "chapters",
    "transcript": "transcript",
    "thumbnail": "thumbnail",
}
REPO_ROOT = Path(__file__).resolve().parents[2]


def hub_version(repo_root: Path = REPO_ROOT) -> str:
    """The Hub version a promotion is pinned to, from pyproject (the SSOT)."""
    pyproject = Path(repo_root) / "pyproject.toml"
    if not pyproject.is_file():
        return "unknown"
    with open(pyproject, "rb") as handle:
        return tomllib.load(handle).get("project", {}).get("version", "unknown")


def promotion_path(out_dir: Path, app: str, date: str) -> Path:
    return Path(out_dir) / f"{app}-{date}.promotion.json"


def promoted_assets(manifest: dict, viewport: str = "desktop") -> dict:
    """The files of the canonical renditions, by language then role."""
    assets = {}
    for rendition in manifest.get("renditions", []):
        if rendition.get("viewport") != viewport or not rendition.get("canonical", True):
            continue
        language = rendition.get("language", "")
        files = {record["role"]: record for record in rendition.get("files", [])}
        entry = {}
        for role, source in PROMOTED_ROLES.items():
            record = files.get(source)
            if record:
                entry[role] = {"name": record["name"], "sha256": record["sha256"],
                               "bytes": record["bytes"]}
        entry["duration_seconds"] = rendition.get("duration_seconds")
        entry["cues"] = rendition.get("cues")
        assets[language] = entry
    return assets


def default_description(out_dir: Path, manifest: dict, language: str) -> str:
    """The render's own words: the title, then the chapter list it was recorded with."""
    name = f"{manifest.get('app')}-{manifest.get('date')}.{language}.txt"
    transcript = Path(out_dir) / name
    if not transcript.is_file():
        return ""
    lines = [line.strip() for line in transcript.read_text(encoding="utf-8").splitlines()]
    title = lines[0] if lines else ""
    chapters = []
    in_chapters = False
    for line in lines:
        if line == "Chapters":
            in_chapters = True
            continue
        if in_chapters:
            if not line:
                break
            chapters.append(line)
    summary = "; ".join(chapters[:6])
    return f"{title}: {summary}" if summary else title


def build_promotion(manifest: dict, *, promoted_by: str, hub_version_value: str,
                    docs_targets: list[str], embed_key: str = "",
                    descriptions: dict[str, str] | None = None, out_dir: Path | None = None,
                    viewport: str = "desktop", promoted_at: str = "",
                    leaf_versions: dict[str, str] | None = None) -> dict:
    """The promotion record for one render, pinned to the manifest's digests."""
    descriptions = dict(descriptions or {})
    assets = promoted_assets(manifest, viewport)
    titles = dict(manifest.get("titles") or {})
    for language in assets:
        if not descriptions.get(language) and out_dir is not None:
            descriptions[language] = default_description(out_dir, manifest, language)
    return {
        "schema": PROMOTION_SCHEMA,
        "app": manifest.get("app"),
        "date": manifest.get("date"),
        "manifest": f"{manifest.get('app')}-{manifest.get('date')}.manifest.json",
        "manifest_sha256": (manifest.get("scenario") or {}).get("sha256", ""),
        "commit": (manifest.get("source") or {}).get("commit", ""),
        "hub_version": hub_version_value,
        # A leaf-app guide is versioned against the leaf too: the Hub commit says
        # nothing about which scitex-writer produced the screen it shows.
        "leaf_versions": dict(leaf_versions or {}),
        "viewport": viewport,
        "promoted_at": promoted_at or datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        "promoted_by": promoted_by.strip(),
        "titles": titles,
        "descriptions": descriptions,
        "docs_targets": list(docs_targets),
        "embed_key": embed_key,
        "assets": assets,
        # Pinned so an embed cannot drift onto a different encode of "the same"
        # walkthrough: the whole point of not re-encoding is that the bytes hold.
        "video_sha256": {
            language: entry.get("video", {}).get("sha256", "")
            for language, entry in assets.items()
        },
    }


def write_promotion(path: Path, promotion: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(promotion, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def load_promotion(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def promotion_for_manifest(manifest_path: Path) -> Path:
    """Where the promotion file for a manifest lives (next to it, same stem)."""
    manifest_path = Path(manifest_path)
    stem = manifest_path.name.removesuffix(".manifest.json")
    return manifest_path.with_name(f"{stem}.promotion.json")


def parse_description(value: str) -> tuple[str, str]:
    language, _, text = value.partition("=")
    if not language or not text:
        raise argparse.ArgumentTypeError("expected LANG=TEXT, for example en=Create a project")
    return language.strip(), text.strip()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a rendered demo video for embedding")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--by", required=True, dest="promoted_by",
                        help="who decided this asset may be embedded")
    parser.add_argument("--docs-page", action="append", default=[],
                        help="docs page that may embed it (repeatable)")
    parser.add_argument("--embed-key", default="", help="catalog key an embed should use")
    parser.add_argument("--description", action="append", default=[], type=parse_description,
                        metavar="LANG=TEXT", help="override a default description (repeatable)")
    parser.add_argument("--hub-version", default="", help="default: pyproject's version")
    parser.add_argument("--viewport", default="desktop")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--check", action="store_true",
                        help="verify the pinned digests against the files, write nothing")
    return parser.parse_args(argv)


def verify_promotion(promotion: dict, out_dir: Path) -> list[str]:
    """Every pinned asset must still be the file it was pinned to."""
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_manifest import file_digest

    problems = []
    for language, entry in (promotion.get("assets") or {}).items():
        for role, record in entry.items():
            if not isinstance(record, dict) or not record.get("name"):
                continue
            on_disk = file_digest(Path(out_dir) / record["name"])
            if on_disk.get("missing"):
                problems.append(f"{language}/{role}: {record['name']} is gone")
            elif on_disk["sha256"] != record.get("sha256"):
                problems.append(f"{language}/{role}: {record['name']} no longer matches its digest")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_manifest import load_manifest

    out_dir = args.manifest.parent
    manifest = load_manifest(args.manifest)
    path = promotion_for_manifest(args.manifest)
    if args.check and path.is_file():
        problems = verify_promotion(load_promotion(path), out_dir)
        for problem in problems:
            print(f"STALE: {problem}", file=sys.stderr)
        print("promotion verified" if not problems else "promotion is stale", file=sys.stderr)
        return 1 if problems else 0
    promotion = build_promotion(
        manifest,
        promoted_by=args.promoted_by,
        hub_version_value=args.hub_version or hub_version(args.repo_root),
        docs_targets=args.docs_page,
        embed_key=args.embed_key,
        descriptions=dict(args.description),
        out_dir=out_dir,
        viewport=args.viewport,
    )
    write_promotion(path, promotion)
    print(f"wrote {path}")
    print(json.dumps(promotion, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
