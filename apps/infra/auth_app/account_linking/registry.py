#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The one seam that writes a human into the scitex-cards user registry.

Everything hub knows about the board's user tables is in this module, so the
coupling has exactly one site to audit and one site to change.

HOW EMAIL-KEYED IDENTITY WORKS WITHOUT A CARDS SCHEMA CHANGE
------------------------------------------------------------
The cards ``user_names`` table is ``name TEXT PRIMARY KEY`` referencing
``users(id)`` — many names collapsing onto one user, globally unique. Putting
the verified email in as a name therefore gives email-keyed lookup whose
uniqueness is enforced by a primary key, and ``add_alias`` already fails loud
when a name belongs to someone else. That is precisely the operator's rule
("key on the email address, not the username") using only the shipped API.

The OIDC ``(issuer, subject)`` pair is deliberately NOT sent over. It has no
column in scitex_cards 0.37.1, and stuffing it into ``record_json`` or the
opaque ``notify`` bag would buy nothing — no uniqueness, no constraint, no
index — while making the store look like it enforces something it does not.
It lives in :mod:`.models` instead. Cards does not need it to attribute a
card; it needs a name, and it now has the best possible one.

FAILURE POLICY — declared states, never a silent pass
-----------------------------------------------------
A board write must NEVER take down a login: the board is downstream of
authentication, and a cards outage that logs everybody out would be a far
worse failure than a missing board row. But "must not break login" is not a
licence to swallow errors, so every outcome is a DECLARED status on a fixed
dataclass, logged at a level that matches its severity, and persisted by the
caller. A row whose ``cards_user_id`` is blank is a visible, queryable
backlog — not an invisible one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: Board-side write outcomes. Each is a state a caller can act on:
#:
#: ``created``      a new cards user was registered for this human
#: ``linked``       the email was added as an alias of an EXISTING cards user
#: ``existing``     the email already resolved to a cards user; nothing to do
#: ``unavailable``  scitex-cards is not installed / its store does not resolve
#: ``conflict``     the email belongs to a DIFFERENT cards user — needs a human
#: ``failed``       the write raised for any other reason
CREATED = "created"
LINKED = "linked"
EXISTING = "existing"
UNAVAILABLE = "unavailable"
CONFLICT = "conflict"
FAILED = "failed"

VALID_OUTCOMES: tuple[str, ...] = (
    CREATED,
    LINKED,
    EXISTING,
    UNAVAILABLE,
    CONFLICT,
    FAILED,
)


@dataclass(frozen=True)
class CardsUpsert:
    """Fixed-shape result of a board-side user upsert.

    Attributes
    ----------
    status : str
        One of :data:`VALID_OUTCOMES`.
    cards_user_id : str | None
        The ``u_*`` id when one is known, else ``None``.
    detail : str
        Human-readable explanation — surfaced in logs and in the admin, never
        parsed.
    """

    status: str
    cards_user_id: str | None
    detail: str

    def __post_init__(self) -> None:
        if self.status not in VALID_OUTCOMES:
            raise ValueError(
                f"invalid upsert status {self.status!r}; must be one of "
                f"{VALID_OUTCOMES}"
            )

    @property
    def ok(self) -> bool:
        """Whether a cards user id was established by or before this call."""
        return self.cards_user_id is not None


def _users_api():
    """Import the cards user API, or raise ``ImportError``.

    Imported lazily and from ONE place. The module is private upstream
    (``scitex_cards._users``) because no public re-export exists yet —
    ``scitex_cards`` itself exports none of ``register_user`` / ``add_alias``
    / ``list_users``. Isolating it here keeps that coupling to a single line
    to change when a public surface lands.
    """
    from scitex_cards import _users

    return _users


def _find_by_exact_name(users, name: str):
    """Exact ``names[]`` match, or ``None``.

    Deliberately NOT ``resolve_user``: that helper widens the search with
    ``canonical_identity``, which strips ``proj-`` prefixes and trailing
    ``-<host>`` suffixes to collapse naming drift. Drift-collapsing is right
    for a card owner typed by a human and WRONG for an account key, where a
    near-match must never resolve. Exact only.
    """
    for user in users:
        if name in (user.names or []):
            return user
    return None


def upsert_cards_user(
    *,
    email: str,
    display_name: str = "",
    host_at_name: str = "",
    store=None,
) -> CardsUpsert:
    """Ensure a cards user exists carrying ``email`` as one of its names.

    Parameters
    ----------
    email : str
        The VERIFIED, normalised address. Callers must not pass an
        unverified one — it becomes an account key on arrival.
    display_name : str, optional
        A human-friendly name to register alongside the email, used only
        when it is not already taken by somebody else.
    host_at_name : str, optional
        Instance namespacing, stored on the cards record.
    store : optional
        Store override, forwarded verbatim; ``None`` uses the resolved store.

    Returns
    -------
    CardsUpsert
        Always a fixed-shape result. Never raises — every failure is a
        declared status, because a board write must not break a login.
    """
    if not email:
        return CardsUpsert(
            status=FAILED,
            cards_user_id=None,
            detail="refusing to upsert a cards user with an empty email",
        )

    try:
        users_api = _users_api()
    except ImportError as exc:
        logger.error(
            "[account-linking] scitex-cards is not importable, so the board "
            "user for %s was NOT written: %s. Logins still work; the row is "
            "recorded with a blank cards_user_id and can be backfilled with "
            "`manage.py seed_cards_identities`.",
            email,
            exc,
        )
        return CardsUpsert(
            status=UNAVAILABLE,
            cards_user_id=None,
            detail=f"scitex_cards not importable: {exc}",
        )

    try:
        users = users_api.list_users(store) if store else users_api.list_users()

        existing = _find_by_exact_name(users, email)
        if existing is not None:
            return CardsUpsert(
                status=EXISTING,
                cards_user_id=existing.id,
                detail=f"email already registered to cards user {existing.id}",
            )

        # The email is unclaimed. If the display name identifies an existing
        # HUMAN, this is the same person arriving via a second provider — add
        # the address to them rather than minting a duplicate.
        if display_name:
            by_name = _find_by_exact_name(users, display_name)
            if by_name is not None:
                if by_name.kind != "human":
                    return CardsUpsert(
                        status=CONFLICT,
                        cards_user_id=None,
                        detail=(
                            f"display name {display_name!r} belongs to cards "
                            f"user {by_name.id} of kind {by_name.kind!r}, not "
                            f"'human' — refusing to attach a person's verified "
                            f"email to a non-human record"
                        ),
                    )
                kwargs = {"store": store} if store else {}
                users_api.add_alias(by_name.id, email, **kwargs)
                logger.info(
                    "[account-linking] linked %s to existing cards user %s",
                    email,
                    by_name.id,
                )
                return CardsUpsert(
                    status=LINKED,
                    cards_user_id=by_name.id,
                    detail=f"email added as an alias of {by_name.id}",
                )

        # Nobody holds either name — register a new human. The email leads
        # the names list so it is the canonical display name, which is the
        # operator's "key on email, not username" rule showing through on the
        # board itself.
        names = [email]
        if display_name and _find_by_exact_name(users, display_name) is None:
            names.append(display_name)

        created = users_api.register_user(
            kind="human",
            names=names,
            host_at_name=host_at_name or None,
            **({"store": store} if store else {}),
        )
        logger.info(
            "[account-linking] registered cards user %s for %s",
            created.id,
            email,
        )
        return CardsUpsert(
            status=CREATED,
            cards_user_id=created.id,
            detail=f"registered cards user {created.id} with names {names}",
        )

    except Exception as exc:  # noqa: BLE001 - see FAILURE POLICY above
        logger.exception(
            "[account-linking] cards user upsert FAILED for %s: %s. The login "
            "succeeded; the identity row keeps a blank cards_user_id.",
            email,
            exc,
        )
        return CardsUpsert(
            status=FAILED,
            cards_user_id=None,
            detail=f"{type(exc).__name__}: {exc}",
        )


__all__ = [
    "CONFLICT",
    "CREATED",
    "EXISTING",
    "FAILED",
    "LINKED",
    "UNAVAILABLE",
    "VALID_OUTCOMES",
    "CardsUpsert",
    "upsert_cards_user",
]

# EOF
