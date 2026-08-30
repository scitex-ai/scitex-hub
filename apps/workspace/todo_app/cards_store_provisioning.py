#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/workspace/todo_app/cards_store_provisioning.py
"""Provisioning guard for the mounted cards board: is there a store to READ?

Extracted from ``middleware.py`` (2026-08-18). That module's job is TENANCY —
resolve the per-request workspace store, discard a client ``?store=``, gate
writes. This one answers a different question that happens to need the same
request hook: whether this deployment has a card store AT ALL, and what to say
when it does not. Nothing here touches request state; it is pure functions over
a path string plus one probe of the resolver.

# --------------------------------------------------------------------------
# THE DEFECT
# --------------------------------------------------------------------------
THE HUB NEVER CONFIGURED ONE, AND NOTHING HERE PRETENDS OTHERWISE. The tenancy
injection in ``middleware.py`` names a per-tenant ``tasks.yaml``, but that path
is the SIDECAR (groups:, cache key, provenance label). Card DATA comes from the
ONE canonical database upstream resolves with no argument — ``load_tasks``
discards the path it is handed and reads ``resolve_db_path(None)``, and
scitex-cards' own ``_django/_request_store.py`` says so in as many words: "On
the CARD path the fallback is inert: ``load_tasks`` discards the resolved store
and reads the one canonical DB ... so no ``?store=`` has ever chosen a card
database."

Since the 2026-08-13 zero-config abolition that resolver REFUSES to invent a
default and raises ``StoreTargetNotConfigured``. Measured on this branch, that
type is a plain ``RuntimeError`` — its MRO parent, not a ``StoreUnavailableError``
subclass — so upstream's typed 404-for-absent / 500-for-outage split in
``api_dispatch`` misses it entirely and it lands in the generic
``except Exception`` -> HTTP 500.

MEASURED, authenticated, CI run 32059143367 (PR #643) artifact
content-report.txt: ``HTTP 500 http://127.0.0.1:8000/apps/cards/graph``, the
only page in the set rendering zero images, while the operator reported
「cards が読み込めていない。」 by eye. Reproduced locally through the real
URLconf with a logged-in user; the whole affected set measured 2026-08-18::

    200  /apps/cards/            page renders its own diagnostic
    500  /apps/cards/graph       <- the defect
    500  /apps/cards/tasks
    500  /apps/cards/rev
    500  /apps/cards/timeline
    500  /apps/cards/runnable
    200  /apps/cards/ping        upstream NO_BOARD_ENDPOINTS, store-free
    200  /apps/cards/dm/threads  request-scoped store — WORKS
    200  /apps/cards/dm/thread/operator
    403  /apps/cards/me/cards    request-scoped store — identity, not a crash
    200  /apps/cards/fleet/ci-status  reads the sac registry, not the board
    200  /apps/cards/chat        page

A 500 here is wrong on three axes and every one of them was paid for: the
visitor is told the PRODUCT is down when this deployment is merely
unconfigured, 5xx reads as "try again" so the board re-polls forever, and a
real outage becomes indistinguishable from a permanent configuration state. So
the refusal is answered as what it is — 404, non-retryable, machine-typed,
carrying the resolver's OWN sentence so the reason survives to whoever is
reading it, plus the hub's own next step. It is NOT converted into an empty
graph: a board that renders 0 cards over an unreadable store is the visual
signature of a wipe.

THIS MODULE IS THE REPORTING HALF ONLY. The CONFIGURATION half lives in
``config.settings._optional_apps.publish_cards_store_target``, which publishes
``$SCITEX_HUB_CARDS_STORE`` as the ``$SCITEX_CARDS_DB`` the package reads. Both
are needed: one gives a deployment a place to state the target, the other makes
the state of having stated nothing legible.
"""

from __future__ import annotations

import logging
import re

from django.http import JsonResponse

logger = logging.getLogger(__name__)

#: Typed discriminator so the board's JS tells this apart from every other 404
#: WITHOUT string-matching prose. Deliberately DIFFERENT from scitex-cards'
#: own ``store_absent``: that one means "the configured store holds nothing for
#: you", this one means "nobody configured a store at all". Collapsing them
#: would render an onboarding message over a deployment defect.
STORE_UNCONFIGURED_REASON = "cards-store-not-configured"

#: THE HUB'S OWN NEXT STEP, because upstream's sentence cannot know it.
#: The resolver names ``$SCITEX_CARDS_DB`` and its own config key — correct,
#: and not what a hub operator sets. On this deployment the target is stated in
#: ``deployment/docker/envs/.env.<env>`` under the hub's ``SCITEX_HUB_*``
#: prefix, and ``config.settings._optional_apps.publish_cards_store_target``
#: hands it to the package. A refusal that omits this leaves the reader with a
#: correct diagnosis and no reachable action, which is the failure mode the
#: constitution names: "name the offending file, value, or version".
#: The variable name is INTERPOLATED from the settings module, never spelled
#: twice — a rename must break the import, not silently print a dead variable.
STORE_UNCONFIGURED_HINT = (
    "On scitex-hub, set {var} in deployment/docker/envs/.env.<env> "
    "(the same file as SCITEX_HUB_POSTGRES_*); it is published as "
    "$SCITEX_CARDS_DB at settings load by "
    "config.settings._optional_apps.publish_cards_store_target. The fleet "
    "convention is a per-host PostgreSQL on port 55432, e.g. "
    "postgresql://scitex_cards@127.0.0.1:55432/scitex_cards -- confirm this "
    "host's own DSN with `scitex-cards resolve-store` rather than copying the "
    "example. NOTE: 5432 is never a scitex port."
)

#: Mount paths that do NOT read the ambient card store, and so must keep
#: working when none is configured. Every entry is measured in the table above,
#: and the exemptions are the point: blanket-refusing the mount would take down
#: the DM surface, which resolves its store from the request and works today —
#: the one thing the operator asked for by name (phone parity, 「読み書き送信…」).
#: Tracks scitex_cards._django.urls in lockstep, same contract as _TODO_PREFIX
#: in ``middleware.py``.
AMBIENT_STORE_EXEMPT = (
    # HTML pages. They pass through so the board still renders and shows its
    # own load-error banner; refusing them would replace a diagnosable page
    # with a raw JSON blob.
    re.compile(r"^/apps/cards/?$"),
    re.compile(r"^/apps/cards/(?:legacy|board-v3|board|chat|dm|me)/?$"),
    re.compile(r"^/apps/cards/favicon\.ico$"),
    # Health check — upstream lists it in NO_BOARD_ENDPOINTS; it never opens
    # a store, and a health probe that fails on configuration is useless.
    re.compile(r"^/apps/cards/ping$"),
    # The REQUEST-SCOPED surfaces: DM, its attachments, and /me/cards read
    # through `_request_store.read_store`, i.e. the store the tenancy
    # middleware injected, not the ambient one. Unaffected by definition.
    re.compile(r"^/apps/cards/dm(?:/.*)?$"),
    re.compile(r"^/apps/cards/attachments/.*$"),
    re.compile(r"^/apps/cards/me/cards$"),
    # Registry reader, not a board reader.
    re.compile(r"^/apps/cards/fleet/ci-status$"),
)


def reads_ambient_card_store(path: str) -> bool:
    """True when this mount path serves data from the AMBIENT card store."""
    return not any(pattern.match(path) for pattern in AMBIENT_STORE_EXEMPT)


def ambient_store_refusal() -> str | None:
    """The store resolver's own refusal sentence, or ``None`` if one is set.

    ONLY ``StoreTargetNotConfigured`` is caught, and the narrowness is the
    contract. Its sibling ``StoreTargetIsNotAPath`` (a malformed
    ``$SCITEX_CARDS_DB``) is a deployment ERROR rather than a steady
    configuration state, and every other failure — a server that is down,
    unreachable or refusing auth — is an OUTAGE. Those must stay loud, stay
    5xx and stay in alerting; widening this except clause would move a dead
    database off 500 along with an unconfigured one, which is the exact
    conflation upstream split ``StoreNotProvisionedError`` out to end.
    """
    try:
        from scitex_cards._store_target import (
            StoreTargetNotConfigured,
            resolve_store_target,
        )
    except ImportError:
        # A scitex-cards older than the 2026-08-13 abolition: its resolver
        # still ANSWERS with a zero-config default and cannot raise this, so
        # there is no refusal for this guard to pre-empt. That is a positive
        # reading of the installed version, not a swallow — on such a build
        # the 500 this guard replaces does not occur.
        return None

    try:
        resolve_store_target(None)
    except StoreTargetNotConfigured as exc:
        return str(exc)
    return None


def store_unconfigured_hint() -> str:
    """The hub-side next step, naming the variable THIS deployment sets."""
    from config.settings._optional_apps import CARDS_STORE_HUB_ENV

    return STORE_UNCONFIGURED_HINT.format(var=f"${CARDS_STORE_HUB_ENV}")


def unconfigured_store_response(path: str) -> JsonResponse | None:
    """The refusal for ``path``, or ``None`` when there is nothing to refuse.

    ``None`` is the overwhelmingly common answer — a configured deployment, or
    a path that never touches the ambient store — and it means "carry on", not
    "we checked and it was fine but say nothing".
    """
    if not reads_ambient_card_store(path):
        return None

    refusal = ambient_store_refusal()
    if refusal is None:
        return None

    # WARNING, not exception(): a configuration state logged as a traceback on
    # every poll is the same monitoring noise in the log rail that the 500 was
    # in the HTTP rail.
    logger.warning(
        "[todo-mount] no cards store configured for %s: %s", path, refusal
    )
    return JsonResponse(
        {
            "error": refusal,
            "reason": STORE_UNCONFIGURED_REASON,
            "hint": store_unconfigured_hint(),
        },
        status=404,
    )


# EOF
