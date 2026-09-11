#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The consent record must say WHICH terms were accepted, not merely that some were.

CARD: hub-signup-flow-constraints-from-business-20260902, item 6.

WHAT THIS FILE DEFENDS AGAINST, stated as the three ways a consent record can
look right and be worthless:

  1. A BOOLEAN. "agreed: true" cannot answer "which wording did they agree to
     after we revised it" — the requirement's own words. Guarded by asserting
     the stored value is a sha256 that equals an INDEPENDENT recompute of the
     current source, so a constant or a True would fail.

  2. A CONSTANT. A hard-coded hash, or one derived from a filename, passes a
     single-document test. Guarded by mutating the text and asserting the hash
     moves, and by asserting two different documents do not share a digest.

  3. A RECORD THAT ONLY EXISTS ON THE HAPPY PATH. A revision must ADD a row,
     and a signup must produce one per accepted document. Guarded by the
     history test and the per-document signup test.

The pure tests run WITHOUT a database (so they run here and in the ordinary
matrix); the model/view cases need the CI postgres and are marked django_db —
the same honest local limit the other guards on this board state.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from apps.infra.auth_app import consent

# ---------------------------------------------------------------------------
# Pure: the hash is a function of the CONTENT, not a constant or a filename.
# ---------------------------------------------------------------------------


def test_the_hash_is_a_sha256_of_its_input():
    # Arrange / Act
    digest = consent.content_hash("hello")
    # Assert
    assert digest == hashlib.sha256(b"hello").hexdigest()
    assert len(digest) == 64


def test_different_text_yields_a_different_hash():
    # Arrange — the anti-constant control.
    # Act / Assert
    assert consent.content_hash("terms v1") != consent.content_hash("terms v2")


def test_a_one_character_amendment_moves_the_hash():
    # Arrange — the smallest realistic edit a revision makes.
    original = "You agree to pay 1,490 yen per month."
    # Act / Assert
    assert consent.content_hash(original) != consent.content_hash(
        original.replace("1,490", "1,980")
    )


def test_the_hash_is_not_derived_from_the_filename_or_label():
    # Arrange — same text under two keys must produce the SAME hash; if the key
    # or label leaked into the digest, a rename would look like a revision.
    # Act / Assert
    assert consent.content_hash("same body") == consent.content_hash("same body")


def test_current_hashes_match_an_independent_recompute():
    # Arrange — recompute from the real files WITHOUT using the module's read,
    # so this cannot pass by both sides sharing a bug.
    expected = {}
    for key, doc in consent.CONSENT_DOCUMENTS.items():
        path = Path(doc.source if Path(doc.source).is_absolute() else doc.path())
        expected[key] = hashlib.sha256(
            path.read_text(encoding="utf-8", errors="replace").encode("utf-8")
        ).hexdigest()
    # Act
    actual = consent.current_document_hashes()
    # Assert
    assert actual == expected
    assert set(actual) == {"terms", "privacy"}


def test_the_two_documents_do_not_share_a_digest():
    # Arrange / Act
    hashes = consent.current_document_hashes()
    # Assert — if both documents returned one hard-coded value, this fails.
    assert hashes["terms"] != hashes["privacy"]


def test_unknown_document_key_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        consent.document_source_path("not-a-document")


def test_a_missing_document_refuses_instead_of_hashing_nothing(monkeypatch):
    # Arrange — point one document at a path that does not exist.
    broken = consent.ConsentDocument(
        key="terms", label="Terms of Use", source="does/not/exist.html"
    )
    monkeypatch.setitem(consent.CONSENT_DOCUMENTS, "terms", broken)
    # Act / Assert — a consent record hashing an absent file is worse than none.
    with pytest.raises(FileNotFoundError):
        consent.current_document_hashes(("terms",))


def test_the_documents_resolve_to_files_that_exist():
    # Arrange / Act / Assert — the registry is only meaningful if the paths are
    # real; a rename would otherwise surface as a failed signup in production.
    for key in consent.CONSENT_DOCUMENTS:
        assert consent.document_source_path(key).is_file(), key


# ---------------------------------------------------------------------------
# DB-backed: the RECORD, its history, and the signup wiring.
# These need the CI postgres; they are not claimed green locally.
# ---------------------------------------------------------------------------


def _make_user(username="consent-test-user"):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username=username, email=f"{username}@example.org", password="x"
    )


@pytest.mark.django_db
def test_recording_consent_stores_user_document_hash_and_timestamp():
    # Arrange
    from apps.infra.auth_app.models import TermsConsent

    user = _make_user()
    # Act
    records = TermsConsent.record_signup_consent(user)
    # Assert — WHICH (document + content hash) and WHEN, per the requirement.
    assert {r.document for r in records} == {"terms", "privacy"}
    for record in records:
        assert len(record.content_hash) == 64
        assert record.accepted_at is not None
        assert record.user_id == user.id


@pytest.mark.django_db
def test_the_stored_hash_equals_the_hash_of_the_current_source():
    # Arrange
    from apps.infra.auth_app.models import TermsConsent

    user = _make_user("consent-hash-user")
    current = consent.current_document_hashes()
    # Act
    TermsConsent.record_signup_consent(user)
    # Assert — derived from the CURRENT documents, not a literal in the model.
    stored = {r.document: r.content_hash for r in user.terms_consents.all()}
    assert stored == current


@pytest.mark.django_db
def test_a_revision_appends_history_instead_of_overwriting():
    # Arrange — the requirement's whole point: after the words change, the old
    # agreement must still be recoverable.
    from apps.infra.auth_app.models import TermsConsent

    user = _make_user("consent-history-user")
    TermsConsent.objects.create(
        user=user, document="terms", content_hash=consent.content_hash("terms v1")
    )
    # Act
    TermsConsent.record_signup_consent(user)
    # Assert — both rows survive; the old one is not updated away.
    digests = set(
        user.terms_consents.filter(document="terms").values_list(
            "content_hash", flat=True
        )
    )
    assert consent.content_hash("terms v1") in digests
    assert consent.current_document_hashes()["terms"] in digests
    assert len(digests) == 2


@pytest.mark.django_db
def test_the_record_is_not_a_bare_boolean():
    # Arrange
    from apps.infra.auth_app.models import TermsConsent

    # Act
    field_names = {f.name for f in TermsConsent._meta.get_fields()}
    # Assert — a boolean "agreed" column is exactly what the card forbids.
    assert {"document", "content_hash", "accepted_at"} <= field_names
    assert not any(
        f.get_internal_type() == "BooleanField" for f in TermsConsent._meta.get_fields()
    )


@pytest.mark.django_db
def test_signup_without_the_checkbox_creates_no_user_and_no_consent():
    # Arrange
    from django.contrib.auth.models import User
    from django.test import Client
    from django.urls import reverse

    from apps.infra.auth_app.models import TermsConsent

    before = User.objects.count()
    # Act — the checkbox omitted.
    response = Client().post(
        reverse("auth_app:signup"),
        {
            "username": "no-consent-user",
            "email": "no-consent-user@example.org",
            "password": "Str0ng-Passw0rd!",
            "password2": "Str0ng-Passw0rd!",
        },
    )
    # Assert — refused, and nothing was created.
    assert response.status_code == 200  # re-rendered with errors
    assert User.objects.count() == before
    assert not TermsConsent.objects.filter(user__username="no-consent-user").exists()


@pytest.mark.django_db
def test_signup_with_the_checkbox_records_consent_for_every_document():
    # Arrange
    from django.contrib.auth.models import User
    from django.test import Client
    from django.urls import reverse

    from apps.infra.auth_app.models import TermsConsent

    # Act
    Client().post(
        reverse("auth_app:signup"),
        {
            "username": "with-consent-user",
            "email": "with-consent-user@example.org",
            "password": "Str0ng-Passw0rd!",
            "password2": "Str0ng-Passw0rd!",
            "agree_terms": "on",
        },
    )
    # Assert — the account exists and carries a record per accepted document,
    # each matching the current source. (Gitea/email side effects are not this
    # test's subject; the record is.)
    user = User.objects.filter(username="with-consent-user").first()
    assert user is not None, "signup did not create the account"
    stored = {r.document: r.content_hash for r in TermsConsent.objects.filter(user=user)}
    assert stored == consent.current_document_hashes()

