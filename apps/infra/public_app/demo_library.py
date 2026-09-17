"""Staff-only demo library: one card per rendered guide, built from its own files.

The public catalog (``VIDEO_CATALOG``) is a hand-kept list of what visitors may
watch. This is the other half: what the team actually has, including what is not
publishable yet — a guide whose Japanese rendition nobody has watched, one whose
scenario has moved, one whose media was replaced by hand. A card here shows the
evidence, not a promise:

* product/app, Hub version and exact commit, so a guide is versioned against a
  release instead of "some time in September";
* JA/EN renditions with duration, cues and viewport;
* the watch state per language, because that is what stands between a recording
  and a publishable one;
* a visibility that is derived — private-draft, reviewed, public-ready — never
  asserted by hand.

Nothing here imports Django: the module reads the manifests, the watch gates and
the promotion files, and the view turns the result into a page. That is what makes
the card rules testable without a database or a browser, and it keeps the "what do
we have" logic in one place instead of in a template.

The manifest schema is the interface (``scitex.demo-video.manifest/1``); the
pipeline writes it, this reads it.
"""

import json
from pathlib import Path

MANIFEST_SCHEMA = "scitex.demo-video.manifest/1"
WATCH_GATE_SCHEMA = "scitex.demo-video.watch-gate/1"
PROMOTION_SCHEMA = "scitex.demo-video.promotion/1"
MANIFEST_SUFFIX = ".manifest.json"
# Derived, in order: a draft nobody watched, a reviewed recording, one that is
# also promoted with the metadata an embed needs.
VISIBILITIES = ("private-draft", "reviewed", "public-ready")
# What a card shows for a promoted asset; the view maps these to its media route.
CARD_ROLES = ("video", "captions", "chapters", "transcript", "thumbnail")


def read_json(path: Path) -> dict:
    """A JSON file as a dict, or {} when it is absent or unreadable."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_manifest(path: Path) -> dict:
    """The manifest at ``path``, or {} unless it declares the schema we read."""
    manifest = read_json(path)
    return manifest if manifest.get("schema") == MANIFEST_SCHEMA else {}


def sidecar(manifest_path: Path, suffix: str) -> Path:
    """`projects-2026-09-17.manifest.json` -> `projects-2026-09-17.<suffix>.json`."""
    manifest_path = Path(manifest_path)
    stem = manifest_path.name.removesuffix(MANIFEST_SUFFIX)
    return manifest_path.with_name(f"{stem}.{suffix}.json")


def rendition_rows(manifest: dict) -> list[dict]:
    """One row per rendition: language, viewport, timing, and its files by role."""
    rows = []
    for rendition in manifest.get("renditions", []):
        files = {record.get("role"): record.get("name") for record in rendition.get("files", [])}
        rows.append(
            {
                "language": rendition.get("language", ""),
                "ui_locale": rendition.get("ui_locale", rendition.get("language", "")),
                "viewport": rendition.get("viewport", "desktop"),
                "canonical": rendition.get("canonical", True),
                "alternate_reason": rendition.get("alternate_reason", ""),
                "duration_seconds": rendition.get("duration_seconds"),
                "cues": rendition.get("cues"),
                "narration_seconds": rendition.get("narration_seconds"),
                "files": {role: files.get(role, "") for role in CARD_ROLES},
                "video_sha256": (files.get("video") or ""),
            }
        )
    return rows


def watch_state(gate: dict) -> dict:
    """Per-language watch state from the gate file; every language, not just some."""
    if gate.get("schema") != WATCH_GATE_SCHEMA:
        return {"state": "no-gate", "required": [], "watched": [], "missing": [],
                "failing": [], "stale": [], "publishable": False}
    required = list(gate.get("required_languages", []))
    watches = gate.get("watches") or {}
    watched = [language for language in required if watches.get(language)]
    failed = [language for language in required
              if (watches.get(language) or {}).get("verdict") not in (None, "pass")]
    missing = [language for language in required if not watches.get(language)]
    stale = [language for language in required
             if watches.get(language)
             and (watches[language].get("artifact_sha256") or "")
             != ((gate.get("artifacts") or {}).get(language) or {}).get("sha256", "")]
    if failed:
        state = "failed"
    elif stale:
        state = "stale"
    elif missing:
        state = "partial" if watched else "unwatched"
    else:
        state = "watched"
    return {
        "state": state,
        "required": required,
        "watched": watched,
        "missing": missing,
        "failing": failed,
        "stale": stale,
        "publishable": bool(required) and not missing and not failed and not stale,
    }


def reviewed(gate_state: dict) -> bool:
    return bool(gate_state.get("publishable"))


def promoted(promotion: dict) -> bool:
    """Promotion is complete when it names an embed and pins the video digests."""
    if promotion.get("schema") != PROMOTION_SCHEMA:
        return False
    if not promotion.get("embed_key") or not promotion.get("docs_targets"):
        return False
    hashes = promotion.get("video_sha256") or {}
    return bool(hashes) and all(hashes.values())


def visibility(gate_state: dict, promotion: dict) -> str:
    """Derived, never hand-set: draft -> reviewed -> public-ready."""
    if not reviewed(gate_state):
        return "private-draft"
    return "public-ready" if promoted(promotion) else "reviewed"


def entry_for(manifest_path: Path, library_dir: Path | None = None) -> dict:
    """One card: what the manifest recorded, plus the gate's and promotion's state."""
    manifest_path = Path(manifest_path)
    manifest = read_manifest(manifest_path)
    if not manifest:
        return {}
    directory = Path(library_dir or manifest_path.parent)
    # An entry may live one level down, one folder per render: two renders of the
    # same app on the same day write the same file names, so a flat directory can
    # only hold one of them (measured 2026-09-17: the light copy overwrote the
    # dark/Japanese draft). The folder is part of the media path, never a way out.
    try:
        relative_parent = manifest_path.parent.resolve().relative_to(directory.resolve())
        folder = "" if str(relative_parent) == "." else str(relative_parent).replace("\\", "/")
    except (OSError, ValueError):
        folder = ""
    gate = read_json(sidecar(manifest_path, "watch-gate"))
    promotion = read_json(sidecar(manifest_path, "promotion"))
    gate_state = watch_state(gate)
    renditions = rendition_rows(manifest)
    return {
        "manifest": manifest_path.name,
        "folder": folder,
        "app": manifest.get("app", ""),
        "date": manifest.get("date", ""),
        "captured_at": manifest.get("generated_at", ""),
        "titles": manifest.get("titles") or {},
        "hub_version": promotion.get("hub_version", ""),
        "leaf_versions": promotion.get("leaf_versions") or {},
        "commit": (manifest.get("source") or {}).get("commit", ""),
        "branch": (manifest.get("source") or {}).get("branch", ""),
        "dirty": (manifest.get("source") or {}).get("dirty", None),
        "languages": sorted({row["language"] for row in renditions}),
        "viewports": sorted({row["viewport"] for row in renditions}),
        "renditions": renditions,
        "narrated": bool((manifest.get("environment") or {}).get("voice")),
        "narration_failures": (manifest.get("environment") or {}).get("narration_failures", {}),
        "caption_font_available": (manifest.get("environment") or {}).get(
            "caption_font_available"
        ),
        "watch": gate_state,
        "promotion": {
            "promoted": promoted(promotion),
            "promoted_by": promotion.get("promoted_by", ""),
            "promoted_at": promotion.get("promoted_at", ""),
            "embed_key": promotion.get("embed_key", ""),
            "docs_targets": promotion.get("docs_targets", []),
            "descriptions": promotion.get("descriptions", {}),
        },
        "visibility": visibility(gate_state, promotion),
        "media_dir": str(directory),
    }


def library_index(directory: Path) -> dict:
    """Every manifest in a directory as a card, newest capture first.

    Manifests are found at the top level and one folder down, so a render can keep
    its own folder (its own copy of same-named files) and still appear here.
    """
    directory = Path(directory)
    paths = sorted(directory.glob(f"*{MANIFEST_SUFFIX}"))
    paths += sorted(directory.glob(f"*/*{MANIFEST_SUFFIX}"))
    entries = [entry_for(path, directory) for path in paths]
    entries = [entry for entry in entries if entry]
    entries.sort(key=lambda entry: (entry["date"], entry["app"], entry["captured_at"]), reverse=True)
    counts = dict.fromkeys(VISIBILITIES, 0)
    for entry in entries:
        counts[entry["visibility"]] = counts.get(entry["visibility"], 0) + 1
    return {
        "directory": str(directory),
        "entries": entries,
        "counts": counts,
        "total": len(entries),
    }


def media_names(entry: dict) -> list[str]:
    """Every file a card can offer, as the path the media route must accept."""
    names = []
    folder = entry.get("folder", "")
    for row in entry.get("renditions", []):
        for name in row.get("files", {}).values():
            if not name:
                continue
            qualified = f"{folder}/{name}" if folder else name
            if qualified not in names:
                names.append(qualified)
    return names


def resolve_media(directory: Path, name: str) -> Path | None:
    """The file a media request may read, or None when it may read nothing.

    The library serves bytes that are not on a public static path, so this is the
    only thing standing between a crafted request and the rest of the filesystem.
    It is a pure function on purpose: the rules are testable without a request, and
    the view does not get to invent its own arithmetic.

    At most one folder level is allowed — enough for one folder per render — and each
    segment is validated: no empty segments, no separators inside a segment, no
    parent or hidden names, nothing absolute. The final path must still resolve
    inside the directory, so a symlink pointing out is refused even when every
    segment looks innocent.
    """
    if not name or name.startswith("/") or name.startswith(".") or "\\" in name:
        return None
    segments = name.split("/")
    if len(segments) > 2:
        return None
    for segment in segments:
        if not segment or segment.startswith(".") or ".." in segment:
            return None
    directory = Path(directory)
    candidate = directory.joinpath(*segments).resolve()
    try:
        root = directory.resolve()
    except OSError:
        return None
    if root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


#: Media types the library may serve, by suffix; anything else is refused rather
#: than guessed, so a stray file cannot be handed out with the wrong content type.
MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".vtt": "text/vtt",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".json": "application/json",
}


def content_type_for(name: str) -> str:
    return MEDIA_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")
