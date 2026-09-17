#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-entry visibility: Internal by default, Anyone-with-link for approved entries only.

One control, not a permission system. An entry is **internal** unless somebody flips it:
internal means the outer @scitex.ai Access plus the inner staff/operator check. An
**approved** entry may be flipped to *Anyone with link*, which mints an opaque read-only
token URL; flipping it back to Internal revokes that token immediately, and flipping it
outward again mints a NEW token, so every previously shared URL stays dead. Draft and
rejected entries are locked internal. The page shows the current visibility and a copy
link; there is no listing, no expiry to manage, and no per-person grants.

What is stored per entry: the SHA-256 of the token, who flipped it and when, the current
visibility, and an audit trail. Never the token itself, never a filesystem path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth.hashers import check_password, make_password

SHARE_SCHEMA = "scitex.demo-video.share/1"
TOKEN_BYTES = 32

INTERNAL = "internal"
ANYONE_WITH_LINK = "anyone-with-link"
VISIBILITIES = (INTERNAL, ANYONE_WITH_LINK)

# Play and captions only: a link is for watching, not for taking the library's files.
SHARED_ROLES = ("video", "captions")


class ShareError(RuntimeError):
    """A refusal: not approved, unknown or dead token, revoked, or a disallowed file."""


def now() -> datetime:
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    """The only form of the token that is ever stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    """A cryptographically random, URL-safe token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def load_store(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"schema": SHARE_SCHEMA, "entries": []}
    try:
        store = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ShareError("the visibility store is unreadable") from None
    if not isinstance(store, dict) or store.get("schema") != SHARE_SCHEMA:
        raise ShareError("not a visibility store")
    if not isinstance(store.get("entries"), list):
        store["entries"] = []
    return store


def save_store(path: Path, store: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")


def find_entry(store: dict, clip_id: str) -> dict | None:
    for entry in store["entries"]:
        if entry.get("clip_id") == clip_id:
            return entry
    return None


# Five wrong entries inside a quarter of an hour is enough friction to notice, and few
# enough that a genuine viewer who misreads a passcode twice is not locked out.
MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 15 * 60


def _blank(clip_id: str) -> dict:
    return {
        "clip_id": str(clip_id),
        "visibility": INTERNAL,
        "passcode_hash": "",
        "grants": [],
        "failed_attempts": [],
        "token_sha256": "",
        "token_created_at": "",
        "token_created_by": "",
        "revoked_at": "",
        "revoked_by": "",
        "audit": [],
    }


def visibility_for(store: dict, clip_id: str) -> str:
    """Internal unless an entry says otherwise: the default is the safe one."""
    entry = find_entry(store, clip_id)
    return (entry or {}).get("visibility", INTERNAL)


def set_visibility(store_path: Path, *, clip_id: str, clip_status: str, visibility: str,
                   by: str, when: datetime | None = None,
                   passcode: str = "") -> tuple[dict, str]:
    """Flip an entry's visibility. Returns the stored entry and the new token, if any.

    The token is returned exactly once, to the caller who flipped the entry outward.
    """
    if not clip_id or not str(clip_id).strip():
        raise ShareError("a visibility change needs an entry")
    if visibility not in VISIBILITIES:
        raise ShareError(f"visibility must be one of {list(VISIBILITIES)}")
    if not by or not str(by).strip():
        raise ShareError("a visibility change needs to name who did it")
    if visibility == ANYONE_WITH_LINK and clip_status != "approved":
        # Draft and rejected entries are locked internal.
        raise ShareError(f"only an approved entry may be shared (this one is {clip_status})")

    moment = when or now()
    store = load_store(store_path)
    entry = find_entry(store, clip_id)
    if entry is None:
        entry = _blank(clip_id)
        store["entries"].append(entry)

    was = entry.get("visibility", INTERNAL)
    if visibility == was and (visibility == INTERNAL or entry.get("token_sha256") and not entry.get("revoked_at")):
        return entry, ""            # nothing to do: the entry is already where it was asked to be

    token = ""
    if visibility == ANYONE_WITH_LINK:
        # A fresh token every time it goes outward: an old link stays dead forever.
        token = new_token()
        entry["token_sha256"] = token_hash(token)
        entry["token_created_at"] = moment.isoformat(timespec="seconds")
        entry["token_created_by"] = str(by).strip()
        entry["revoked_at"] = ""
        entry["revoked_by"] = ""
        # Optional passcode, default none. Only the Django hash is kept: the plaintext is
        # typed into a masked field by whoever flips the toggle, and is never stored,
        # logged or rendered - not even in this function's return value.
        entry["passcode_hash"] = make_password(passcode) if passcode else ""
        entry["grants"] = []
        entry["failed_attempts"] = []
    else:
        # Back to internal: the token dies now, not at some expiry, and every grant with
        # it - a viewer who was let in through the link loses that access here.
        entry["token_sha256"] = ""
        entry["token_created_at"] = ""
        entry["token_created_by"] = ""
        entry["passcode_hash"] = ""
        entry["grants"] = []
        entry["revoked_at"] = moment.isoformat(timespec="seconds")
        entry["revoked_by"] = str(by).strip()

    entry["visibility"] = visibility
    entry["audit"].append({
        "at": moment.isoformat(timespec="seconds"),
        "by": str(by).strip(),
        "from": was,
        "to": visibility,
        "token": "minted" if token else "revoked",
        "passcode": "set" if (token and passcode) else ("none" if token else "cleared"),
    })
    save_store(store_path, store)
    return entry, token


def is_publicly_shared(store: dict, clip_id: str) -> bool:
    entry = find_entry(store, clip_id)
    return bool(entry) and entry.get("visibility") == ANYONE_WITH_LINK \
        and bool(entry.get("token_sha256")) and not entry.get("revoked_at")


def find_by_token(store: dict, token: str) -> dict:
    """The entry a token belongs to, compared in constant time over hashes."""
    if not token or not isinstance(token, str):
        raise ShareError("no token")
    wanted = token_hash(token)
    for entry in store["entries"]:
        if hmac.compare_digest(str(entry.get("token_sha256", "")), wanted):
            return entry
    raise ShareError("unknown link")


def view_share(store_path: Path, token: str, clip_lookup, grant: str = "") -> dict:
    """Resolve a token to the entry it may show, or refuse.

    ``clip_lookup(clip_id)`` returns the catalog entry or None. A link never outlives the
    approval it was minted from: if the entry is no longer approved, the link is dead.
    """
    store = load_store(store_path)
    entry = find_by_token(store, token)
    if entry.get("visibility") != ANYONE_WITH_LINK or entry.get("revoked_at"):
        raise ShareError("this link is no longer active")
    if entry.get("passcode_hash") and not has_grant(store, entry.get("clip_id", ""), grant):
        # No passcode, no content: the link alone is not the whole key when one was set.
        raise ShareError("this link asks for a passcode")
    clip = clip_lookup(entry.get("clip_id", ""))
    if not clip:
        raise ShareError("the shared entry is gone")
    if clip.get("status") != "approved":
        raise ShareError("the shared entry is no longer approved")
    return {"clip": clip, "entry": entry}


def needs_passcode(store: dict, clip_id: str) -> bool:
    """Whether this entry's link asks for a passcode at all."""
    entry = find_entry(store, clip_id) or {}
    return bool(entry.get("passcode_hash"))


def failed_recently(entry: dict, when: datetime) -> bool:
    """Whether this entry has had too many wrong passcodes lately."""
    attempts = [stamp for stamp in (entry.get("failed_attempts") or []) if isinstance(stamp, str)]
    recent = 0
    for stamp in attempts:
        try:
            if (when - datetime.fromisoformat(stamp)).total_seconds() <= ATTEMPT_WINDOW_SECONDS:
                recent += 1
        except ValueError:
            continue
    return recent >= MAX_FAILED_ATTEMPTS


def enter_passcode(store_path: Path, clip_id: str, passcode: str, *,
                   when: datetime | None = None) -> str:
    """Exchange a correct passcode for a share-specific grant code, shown once.

    Five wrong entries inside the window stop further tries: this is friction against
    accidental sharing, not a vault, so the limit is about noticing rather than about
    resisting an attacker.
    """
    moment = when or now()
    store = load_store(store_path)
    entry = find_entry(store, clip_id)
    if entry is None:
        raise ShareError("unknown link")
    if failed_recently(entry, moment):
        raise ShareError("too many wrong passcodes: try again later")
    if not entry.get("passcode_hash"):
        raise ShareError("this link does not ask for a passcode")
    if not isinstance(passcode, str) or not check_password(passcode, entry["passcode_hash"]):
        entry.setdefault("failed_attempts", []).append(moment.isoformat(timespec="seconds"))
        save_store(store_path, store)
        raise ShareError("that passcode is not correct")
    grant = new_token()
    entry.setdefault("grants", []).append({
        "grant_sha256": token_hash(grant),
        "at": moment.isoformat(timespec="seconds"),
    })
    entry["failed_attempts"] = []
    save_store(store_path, store)
    return grant


def has_grant(store: dict, clip_id: str, grant: str) -> bool:
    """Whether a grant code came from this entry's passcode exchange."""
    if not grant or not isinstance(grant, str):
        return False
    entry = find_entry(store, clip_id) or {}
    wanted = token_hash(grant)
    return any(hmac.compare_digest(str(record.get("grant_sha256", "")), wanted)
               for record in entry.get("grants") or [])


def shared_media_name(clip: dict, requested: str, folder: str = "") -> str:
    """The one file a link may stream, or a refusal.

    Play and captions only: a viewing link must not become a way to pull the chapters, the
    transcript or the thumbnail out of the library, and it cannot reach another entry's
    media because only this entry's own file names are accepted.
    """
    if not requested or not isinstance(requested, str):
        raise ShareError("no file requested")
    if "/" in requested or "\\" in requested or ".." in requested:
        raise ShareError("a shared file is named without a path")
    offered = set()
    for rendition in clip.get("renditions") or []:
        files = rendition.get("files") or {}
        for role in SHARED_ROLES:
            name = files.get(role) or ""
            if name:
                offered.add(name)
    if requested not in offered:
        raise ShareError("that file is not part of this entry")
    return f"{folder}/{requested}" if folder else requested
