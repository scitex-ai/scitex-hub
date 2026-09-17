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

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

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


def manifest_problems(manifest: object) -> list[str]:
    """Why this cannot be read as a render manifest; empty when it can.

    A schema string is not enough. The review's malformed-manifest case declared the
    right schema and the wrong shapes — ``renditions`` as a string, a file record that
    was not an object — and the index raised while formatting it, which is a 500 on a
    staff page. Every shape the readers index is checked here, once, and the readers
    are defensive anyway because a manifest is an input like any other.
    """
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return ["not a JSON object"]
    if manifest.get("schema") != MANIFEST_SCHEMA:
        return [f"schema is {manifest.get('schema')!r}, not {MANIFEST_SCHEMA!r}"]

    for key in ("app", "date", "commit"):
        if not isinstance(manifest.get(key, ""), str):
            problems.append(f"{key} is not a string")

    renditions = manifest.get("renditions")
    if not isinstance(renditions, list) or not renditions:
        problems.append("renditions is not a non-empty list")
        return problems

    for index, rendition in enumerate(renditions):
        if not isinstance(rendition, dict):
            problems.append(f"rendition {index} is not an object")
            continue
        for key in ("language", "viewport"):
            if not isinstance(rendition.get(key, ""), str):
                problems.append(f"rendition {index} {key} is not a string")
        if not isinstance(rendition.get("canonical", True), bool):
            problems.append(f"rendition {index} canonical is not a boolean")
        files = rendition.get("files")
        if not isinstance(files, list):
            problems.append(f"rendition {index} files is not a list")
            continue
        for position, record in enumerate(files):
            if not isinstance(record, dict):
                problems.append(f"rendition {index} file {position} is not an object")
                continue
            for key in ("role", "name"):
                if not isinstance(record.get(key, ""), str):
                    problems.append(
                        f"rendition {index} file {position} {key} is not a string"
                    )
    return problems


def read_manifest(path: Path) -> dict:
    """The manifest at ``path``, or {} unless it can actually be read and indexed.

    Shapes are validated too (``manifest_problems``): a manifest that declares our
    schema but cannot be indexed is reported as unreadable, the same as a missing file.
    The failure this closes was a manifest that was malformed *and* still reached the
    index.
    """
    manifest = read_json(path)
    if manifest_problems(manifest):
        return {}
    return manifest


def safe_docs_target(value: object) -> str:
    """A documentation link we are willing to render, or "" to drop it.

    Promoted assets link to the guides that explain them, and those links were rendered
    unexamined: a file carrying ``javascript:...`` became a live target in a staff page.
    Accept a site-relative path (not protocol-relative, which leaves the site) or an
    absolute http(s) URL; drop everything else.
    """
    if not isinstance(value, str):
        return ""
    target = value.strip()
    if not target or any(character in target for character in "\r\n\t"):
        return ""
    if target.startswith("/") and not target.startswith("//"):
        return target
    parsed = urlparse(target)
    if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
        return target
    return ""


def sidecar(manifest_path: Path, suffix: str) -> Path:
    """`projects-2026-09-17.manifest.json` -> `projects-2026-09-17.<suffix>.json`."""
    manifest_path = Path(manifest_path)
    stem = manifest_path.name.removesuffix(MANIFEST_SUFFIX)
    return manifest_path.with_name(f"{stem}.{suffix}.json")


def rendition_rows(manifest: dict) -> list[dict]:
    """One row per rendition: language, viewport, timing, and its files by role."""
    rows = []
    for rendition in (manifest.get("renditions") or []):
        if not isinstance(rendition, dict):
            continue
        records = rendition.get("files") or []
        files = {
            record.get("role"): record.get("name")
            for record in records
            if isinstance(record, dict)
        }
        # The manifest records a digest and a size per file. The card used to put the
        # file NAME in a field called video_sha256, so nothing ever compared the bytes
        # on disk with what was recorded, and an approval survived a replaced video.
        file_records = {
            record.get("role", ""): {
                "name": record.get("name", ""),
                "sha256": record.get("sha256", ""),
                "size": record.get("size"),
                "seconds": record.get("seconds"),
            }
            for record in records
            if isinstance(record, dict)
        }
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
                "file_records": {
                    role: file_records.get(role, {"name": "", "sha256": "", "size": None,
                                                  "seconds": None})
                    for role in CARD_ROLES
                },
                "video_sha256": (file_records.get("video") or {}).get("sha256", ""),
            }
        )
    return rows


def watch_state(gate: dict) -> dict:
    """Per-language watch state from the gate file; every language, not just some."""
    if gate.get("schema") != WATCH_GATE_SCHEMA:
        return {"state": "no-gate", "required": [], "watched": [], "missing": [],
                "failing": [], "stale": [], "publishable": False}
    required = [
        language
        for language in (gate.get("required_languages") or [])
        if isinstance(language, str)
    ]
    watches = gate.get("watches") if isinstance(gate.get("watches"), dict) else {}
    artifacts = gate.get("artifacts") if isinstance(gate.get("artifacts"), dict) else {}
    watched = [language for language in required if watches.get(language)]
    failed = [language for language in required
              if (watches.get(language) or {}).get("verdict") not in (None, "pass")]
    missing = [language for language in required if not watches.get(language)]
    stale = [language for language in required
             if watches.get(language)
             and (watches[language].get("artifact_sha256") or "")
             != ((artifacts.get(language) or {}).get("sha256", "")
                 if isinstance(artifacts.get(language), dict) else "")]
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


def sha256_file(path: Path) -> str:
    """The digest of the bytes on disk right now, or "" when they cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return ""
    return digest.hexdigest()


def bytes_match(path: Path, expected: str) -> bool:
    """Whether the file at ``path`` is the file whose digest was recorded.

    An approval is a statement about specific bytes. Re-checking it here is what makes
    a hand-replaced video lose its approval instead of inheriting one: the review's
    finding was that nothing compared the record with the file.
    """
    expected = (expected or "").strip().lower()
    if not expected or len(expected) != 64:
        return False
    return sha256_file(path) == expected


def verify_renditions(directory: Path, rows: list[dict], folder: str = "") -> dict:
    """Per-language: is the video on disk still the video the manifest recorded?

    A language with no recorded digest is reported as unverified rather than trusted —
    "we cannot tell" must never read as "fine".
    """
    base = Path(directory)
    if folder:
        base = base / folder
    verified: dict[str, dict] = {}
    for row in rows:
        language = row.get("language", "")
        record = (row.get("file_records") or {}).get("video") or {}
        name = record.get("name", "")
        expected = record.get("sha256", "")
        if not name or not expected:
            verified[language] = {"name": name, "expected": expected, "actual": "",
                                  "matches": False, "reason": "no recorded digest"}
            continue
        candidate = base / name
        try:
            contained = candidate.resolve().is_relative_to(base.resolve())
        except (OSError, ValueError):
            contained = False
        if not contained:
            verified[language] = {"name": name, "expected": expected, "actual": "",
                                  "matches": False, "reason": "outside the library"}
            continue
        actual = sha256_file(candidate)
        verified[language] = {
            "name": name, "expected": expected, "actual": actual,
            "matches": bool(actual) and actual == expected,
            "reason": "" if actual == expected else ("unreadable" if not actual else "changed"),
        }
    return verified


def identity_problems(manifest: dict, gate: dict, promotion: dict) -> list[str]:
    """Why a gate or promotion file does not belong to this manifest.

    Sidecars are read by file name, so a gate from another render of the same app on
    the same day sits where this manifest looks for one. Binding them is the difference
    between "this asset was reviewed" and "something next to this asset was reviewed".
    """
    problems: list[str] = []
    app, date = manifest.get("app", ""), manifest.get("date", "")
    commit = (manifest.get("source") or {}).get("commit", "")
    digests = {
        row["language"]: (row.get("file_records") or {}).get("video", {}).get("sha256", "")
        for row in rendition_rows(manifest)
    }

    if gate:
        identity = gate.get("manifest")
        if not isinstance(identity, dict):
            problems.append("the gate does not name the manifest it reviewed")
        else:
            if identity.get("app") != app or identity.get("date") != date:
                problems.append(
                    f"the gate names {identity.get('app')}/{identity.get('date')}, "
                    f"not {app}/{date}"
                )
            if identity.get("commit") and commit and identity["commit"] != commit:
                problems.append("the gate was recorded against a different commit")
        for language, artifact in (gate.get("artifacts") or {}).items():
            if not isinstance(artifact, dict):
                problems.append(f"the gate's {language} artifact is not an object")
                continue
            recorded = digests.get(language, "")
            if not recorded:
                problems.append(f"the gate covers {language}, which this render has not")
            elif artifact.get("sha256") != recorded:
                problems.append(
                    f"the gate's {language} digest is not this render's {language} video"
                )

    if promotion:
        if promotion.get("app") and promotion["app"] != app:
            problems.append("the promotion names a different app")
        if promotion.get("date") and promotion["date"] != date:
            problems.append("the promotion names a different date")
        hashes = promotion.get("video_sha256")
        if isinstance(hashes, dict):
            for language, recorded in hashes.items():
                if digests.get(language) != recorded:
                    problems.append(
                        f"the promotion's {language} digest is not this render's video"
                    )
    return problems


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
    bytes_state = verify_renditions(directory, renditions, folder)
    problems = identity_problems(manifest, gate, promotion)
    # A gate that reviewed other bytes, or that names another render, cannot approve
    # this one: the state is derived from the files in front of us, every read.
    unverified = sorted(
        language for language, state in bytes_state.items() if not state.get("matches")
    )
    gate_state = dict(gate_state)
    gate_state["unverified_bytes"] = unverified
    gate_state["identity_problems"] = problems
    if gate_state.get("publishable") and (unverified or problems):
        gate_state["publishable"] = False
        gate_state["state"] = "changed" if unverified else "mismatched"
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
        "bytes_verified": bool(bytes_state) and not unverified,
        "bytes": bytes_state,
        "identity_problems": problems,
        "promotion": {
            "promoted": promoted(promotion),
            "promoted_by": promotion.get("promoted_by", ""),
            "promoted_at": promotion.get("promoted_at", ""),
            "embed_key": promotion.get("embed_key", ""),
            "docs_targets": [
                target
                for target in (
                    safe_docs_target(value)
                    for value in (promotion.get("docs_targets") or [])
                )
                if target
            ],
            "descriptions": promotion.get("descriptions", {}),
        },
        "visibility": visibility(gate_state, promotion),
        "media_dir": str(directory),
    }


def manifest_is_inside(path: Path, root: Path) -> bool:
    """Whether a discovered manifest is really inside the library root.

    The review found discovery following a symlink: a manifest outside the root was
    indexed, and the containment failure was passed over instead of reported. A
    symlinked manifest is skipped here — the index models what the library holds, not
    what a link points at — and a path that cannot be resolved is skipped too.
    """
    path = Path(path)
    try:
        if path.is_symlink():
            return False
        path.resolve().relative_to(root)
    except (OSError, ValueError):
        return False
    return True


def library_index(directory: Path) -> dict:
    """Every manifest in a directory as a card, newest capture first.

    Manifests are found at the top level and one folder down, so a render can keep
    its own folder (its own copy of same-named files) and still appear here.
    """
    directory = Path(directory)
    root = directory.resolve()
    candidates = sorted(directory.glob(f"*{MANIFEST_SUFFIX}"))
    candidates += sorted(directory.glob(f"*/*{MANIFEST_SUFFIX}"))
    paths = [path for path in candidates if manifest_is_inside(path, root)]
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
