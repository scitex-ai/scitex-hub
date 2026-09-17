#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One toggle per entry: Internal by default, Anyone-with-link for approved entries only.

Every test here is one of the operator's rules, including the negative ones — what a link
may NOT reach, and what happens to the link that existed a moment ago.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

import demo_share  # noqa: E402
from demo_share import (  # noqa: E402
    ANYONE_WITH_LINK, INTERNAL, ShareError, enter_passcode, load_store, set_visibility,
    shared_media_name, view_share, visibility_for,
)

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
CLIP_ID = "projects-2026-09-17-abc12345"


def a_clip(status="approved", folder=""):
    return {
        "id": CLIP_ID,
        "status": status,
        "folder": folder,
        "renditions": [
            {"language": "en", "files": {"video": "projects.en.mp4",
                                         "captions": "projects.en.vtt",
                                         "chapters": "projects.en.chapters.vtt",
                                         "transcript": "projects.en.txt",
                                         "thumbnail": "projects.en.thumbnail.png"}}
        ],
    }


def lookup(clip):
    return lambda clip_id: clip if clip_id == CLIP_ID else None


def test_an_entry_is_internal_until_somebody_flips_it(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    # Act
    entry, token = set_visibility(store, clip_id=CLIP_ID, clip_status="draft",
                                  visibility=INTERNAL, by="operator", when=NOW)
    # Assert
    assert entry["visibility"] == INTERNAL
    assert token == ""                     # internal mints nothing
    assert visibility_for(load_store(store), CLIP_ID) == INTERNAL
    assert demo_share.is_publicly_shared(load_store(store), CLIP_ID) is False


def test_draft_and_rejected_entries_are_locked_internal(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    # Act / Assert
    for status in ("draft", "rejected", "unknown"):
        with pytest.raises(ShareError):
            set_visibility(store, clip_id=CLIP_ID, clip_status=status,
                           visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    assert not store.exists()              # a refused flip leaves nothing behind


def test_an_approved_entry_can_be_flipped_outward_and_back(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    # Act: outward
    entry, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                                  visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Assert: a link works while the entry is outward
    assert entry["visibility"] == ANYONE_WITH_LINK
    assert token and len(token) > 20
    assert view_share(store, token, lookup(a_clip()))["entry"]["clip_id"] == CLIP_ID
    # Act: back to internal
    entry, none_minted = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                                        visibility=INTERNAL, by="operator", when=NOW)
    # Assert: the token is dead immediately, and the audit says who did it
    assert none_minted == ""
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip()))
    assert [step["token"] for step in entry["audit"]] == ["minted", "revoked"]
    assert [step["to"] for step in entry["audit"]] == [ANYONE_WITH_LINK, INTERNAL]


def test_flipping_outward_again_mints_a_new_token_and_keeps_the_old_one_dead(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    first, token_one = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                                      visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    set_visibility(store, clip_id=CLIP_ID, clip_status="approved", visibility=INTERNAL,
                   by="operator", when=NOW)
    # Act
    second, token_two = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                                       visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Assert
    assert token_two != token_one
    with pytest.raises(ShareError):
        view_share(store, token_one, lookup(a_clip()))
    assert view_share(store, token_two, lookup(a_clip()))["entry"]["clip_id"] == CLIP_ID
    assert second["token_sha256"] == demo_share.token_hash(token_two)


def test_the_store_holds_a_hash_and_the_audit_and_never_the_token_or_a_path(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    # Act
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Assert
    raw = store.read_text(encoding="utf-8")
    assert token not in raw
    stored = load_store(store)["entries"][0]
    assert stored["token_sha256"] == demo_share.token_hash(token)
    assert stored["token_created_by"] == "operator"
    # The passcode hash, the grant hashes and the failed-attempt stamps are hashes and
    # timestamps: still nothing here is a secret in the clear, and still no path.
    assert set(stored) == {"clip_id", "visibility", "token_sha256", "token_created_at",
                           "token_created_by", "revoked_at", "revoked_by", "audit",
                           "passcode_hash", "grants", "failed_attempts"}
    assert ".mp4" not in raw and "/" not in json.dumps(stored.get("clip_id"))


def test_a_link_dies_with_the_approval_it_was_minted_from(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Act / Assert
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip(status="rejected")))
    with pytest.raises(ShareError):
        view_share(store, token, lambda clip_id: None)


def test_an_unknown_token_is_refused(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                   visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Act / Assert
    for bad in ("", "not-a-token", demo_share.new_token(), None):
        with pytest.raises(ShareError):
            view_share(store, bad, lookup(a_clip()))


def test_a_link_reaches_the_video_and_its_captions_only():
    # Arrange
    clip = a_clip()
    # Act / Assert
    assert shared_media_name(clip, "projects.en.mp4") == "projects.en.mp4"
    assert shared_media_name(clip, "projects.en.vtt") == "projects.en.vtt"
    assert shared_media_name(clip, "projects.en.mp4", folder="take1") == "take1/projects.en.mp4"
    for disallowed in ("projects.en.chapters.vtt", "projects.en.txt",
                       "projects.en.thumbnail.png", "projects.ja.mp4"):
        with pytest.raises(ShareError):
            shared_media_name(clip, disallowed)


def test_a_link_cannot_be_talked_into_a_path_or_another_entry():
    # Arrange
    clip = a_clip()
    # Act / Assert
    for hostile in ("../projects.en.mp4", "take1/../projects.en.mp4", "/etc/passwd",
                    "..%2fprojects.en.mp4", "", None, "other-entry.en.mp4"):
        with pytest.raises(ShareError):
            shared_media_name(clip, hostile)


def test_nothing_lists_the_links_and_visibility_changes_need_a_name(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    # Act / Assert: a listing function would defeat an opaque token.
    for name in dir(demo_share):
        assert not name.startswith("list_"), name
        assert "enumerate" not in name.lower(), name
    with pytest.raises(ShareError):
        set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                       visibility=ANYONE_WITH_LINK, by="", when=NOW)
    with pytest.raises(ShareError):
        set_visibility(store, clip_id="", clip_status="approved",
                       visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    with pytest.raises(ShareError):
        set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                       visibility="public-everywhere", by="operator", when=NOW)


def test_a_link_without_a_passcode_behaves_as_before(tmp_path):
    # Arrange: the default is no passcode, and it must stay a one-click share.
    store = tmp_path / "visibility.json"
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Act / Assert
    assert view_share(store, token, lookup(a_clip()))["clip"]["id"] == CLIP_ID


def test_a_passcode_is_required_when_one_was_set_and_only_its_hash_is_kept(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW,
                              passcode="open-sesame")
    # Act / Assert: the link alone is refused, and the plaintext is nowhere in the store.
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip()))
    raw = store.read_text(encoding="utf-8")
    assert "open-sesame" not in raw
    entry = load_store(store)["entries"][0]
    assert entry["passcode_hash"].startswith("pbkdf2_")
    assert entry["audit"][0]["passcode"] == "set"


def test_a_correct_passcode_grants_a_viewer_and_a_wrong_one_is_counted(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW,
                              passcode="open-sesame")
    # Act: a wrong passcode is refused and recorded; the right one yields a grant.
    with pytest.raises(ShareError):
        enter_passcode(store, CLIP_ID, "guess", when=NOW)
    assert len(load_store(store)["entries"][0]["failed_attempts"]) == 1
    grant = enter_passcode(store, CLIP_ID, "open-sesame", when=NOW)
    # Assert: the grant opens the link, and a wrong one does not.
    assert view_share(store, token, lookup(a_clip()), grant=grant)["clip"]["id"] == CLIP_ID
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip()), grant="not-a-grant")
    assert "open-sesame" not in store.read_text(encoding="utf-8")


def test_repeated_wrong_passcodes_are_rate_limited(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                   visibility=ANYONE_WITH_LINK, by="operator", when=NOW, passcode="open-sesame")
    # Act: five wrong tries, then a sixth that is refused before it is even checked.
    for _ in range(5):
        with pytest.raises(ShareError):
            enter_passcode(store, CLIP_ID, "guess", when=NOW)
    with pytest.raises(ShareError) as refused:
        enter_passcode(store, CLIP_ID, "open-sesame", when=NOW)
    # Assert
    assert "too many wrong passcodes" in str(refused.value)
    # and the limit is a window, not a permanent lock
    from datetime import timedelta
    grant = enter_passcode(store, CLIP_ID, "open-sesame", when=NOW + timedelta(minutes=16))
    assert grant


def test_toggling_back_to_internal_revokes_the_token_and_every_grant(tmp_path):
    # Arrange
    store = tmp_path / "visibility.json"
    _, token = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                              visibility=ANYONE_WITH_LINK, by="operator", when=NOW,
                              passcode="open-sesame")
    grant = enter_passcode(store, CLIP_ID, "open-sesame", when=NOW)
    # Act
    set_visibility(store, clip_id=CLIP_ID, clip_status="approved", visibility=INTERNAL,
                   by="operator", when=NOW)
    # Assert: the link is dead, the grants are gone, and the passcode hash with them.
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip()), grant=grant)
    entry = load_store(store)["entries"][0]
    assert entry["grants"] == [] and entry["passcode_hash"] == ""
    # Act again: going outward mints a new token and no passcode unless one is given.
    _, second = set_visibility(store, clip_id=CLIP_ID, clip_status="approved",
                               visibility=ANYONE_WITH_LINK, by="operator", when=NOW)
    # Assert
    assert second != token
    assert view_share(store, second, lookup(a_clip()))["clip"]["id"] == CLIP_ID
    with pytest.raises(ShareError):
        view_share(store, token, lookup(a_clip()))
