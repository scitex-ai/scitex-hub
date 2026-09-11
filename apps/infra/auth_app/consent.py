#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terms/privacy consent: WHICH version was accepted, not merely THAT it was.

CARD: hub-signup-flow-constraints-from-business-20260902, item 6 (claimed
scope — items 1-5 and 7-15 are explicitly out of scope).

THE REQUIREMENT, verbatim from the card:
    "Terms + privacy consent is a REQUIRED checkbox, and the consent record
     stores WHEN and WHICH VERSION (id or content hash) was accepted — a bare
     boolean cannot show what was agreed to after the terms are revised.
     Hub-side shape: hash the rendered terms/privacy source; store
     (user, doc, hash, ts)."

WHAT WAS MEASURED BEFORE WRITING THIS (the gap it closes):
  - the checkbox exists and is required — ``SignupForm.agree_terms``
    (forms.py:39, ``required=True``);
  - but a grep for consent / accepted_terms / terms_version / terms_hash /
    doc_hash across auth_app + accounts_app (excl. migrations) returned
    NOTHING, so the accepted version was unrecoverable the moment the terms
    changed. That is the defect.

WHY A CONTENT HASH AND NOT A VERSION NUMBER. A hand-maintained version string
only moves when someone remembers to move it, and the failure mode is silent:
the terms change, the number does not, and the record then asserts something
false. Hashing the document source moves exactly when the wording moves,
requires no discipline, and is verifiable from the repository alone — the
tests recompute it independently rather than trusting this module.

WHAT "THE SOURCE" MEANS HERE, stated precisely rather than loosely: this hashes
the document's TEMPLATE SOURCE — the legal text a reader is shown, which is
what the consent is about. It deliberately does NOT hash the whole rendered
page, because that would also move on unrelated chrome (nav copy, footer, i18n
catalogue), and a hash that changes for reasons unrelated to the agreement is a
hash nobody can interpret. The boundary is the legal text.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

__all__ = [
    "CONSENT_DOCUMENTS",
    "ConsentDocument",
    "content_hash",
    "current_document_hashes",
    "document_source_path",
]


@dataclass(frozen=True)
class ConsentDocument:
    """One agreement a registrant can accept."""

    key: str
    label: str
    source: str  # path relative to BASE_DIR

    def path(self) -> Path:
        return Path(settings.BASE_DIR) / self.source


#: ``key -> ConsentDocument``. The key is what lands in
#: ``TermsConsent.document``; the label is what a human reads. Kept next to the
#: hash so a new document is one line and cannot be half-added.
CONSENT_DOCUMENTS: dict[str, ConsentDocument] = {}


def _register(key: str, label: str, source: str) -> None:
    CONSENT_DOCUMENTS[key] = ConsentDocument(key=key, label=label, source=source)


_register(
    "terms",
    "Terms of Use",
    "apps/infra/public_app/templates/public_app/legal/terms_of_use.html",
)
_register(
    "privacy",
    "Privacy Policy",
    "apps/infra/public_app/templates/public_app/legal/privacy_policy.html",
)


def document_source_path(key: str) -> Path:
    """The on-disk source of document ``key``.

    Raises for an unknown key rather than returning a default: a consent
    recorded against a document nobody defined is not a record.
    """
    try:
        return CONSENT_DOCUMENTS[key].path()
    except KeyError:
        raise KeyError(
            f"unknown consent document {key!r}; known: {sorted(CONSENT_DOCUMENTS)}"
        ) from None


def content_hash(text: str) -> str:
    """SHA-256 hex of ``text``, as stored on the record.

    Separated from the file read so a test can prove the hash is a function of
    the CONTENT (different text -> different hash) without touching disk — the
    anti-constant control.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_document_hashes(keys: "tuple[str, ...] | None" = None) -> dict[str, str]:
    """``{key: sha256}`` for the documents as they stand right now.

    Reads the source with ``errors="replace"`` so a stray byte in a legal file
    cannot make registration fail; the hash still moves when the text moves.
    Raises ``FileNotFoundError`` with the resolved path if a document is
    missing — a consent flow that records a hash of nothing is worse than one
    that refuses.
    """
    keys = tuple(CONSENT_DOCUMENTS) if keys is None else keys
    hashes: dict[str, str] = {}
    for key in keys:
        path = document_source_path(key)
        if not path.is_file():
            raise FileNotFoundError(
                f"consent document {key!r} not found at {path}; the signup "
                "consent record would be a hash of nothing."
            )
        hashes[key] = content_hash(path.read_text(encoding="utf-8", errors="replace"))
    return hashes
