#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Webhook PROCESSING idempotency: claim, apply once, release on failure.

Card: hub-signup-email-stripe-funnel-20260917. PR #934 review, blocker 6.

THE DEFECT. The view did::

    _, created = BillingEvent.objects.get_or_create(event_id=...)
    provider.handle_event(event)          # <-- unconditional

``get_or_create`` deduplicated the ROW, and then the handler ran anyway. A
Stripe retry (which is the normal case: Stripe retries every non-2xx, and can
redeliver a 2xx'd event too) therefore re-ran the side effects — re-applying
card state and re-activating entitlement. The event id was known and unused.

THE FIX, and why it is a state machine rather than a flag. "Have we seen this
event?" is not the question; "has this event's work been DONE, and is anyone
doing it right now?" is. Three states, one transition each:

  * ``received`` / ``failed``            -> a worker may CLAIM it
  * ``processing`` (claim held)          -> nobody else may touch it
  * ``processed``                        -> nobody may ever apply it again

A claim is a LEASE, not a permanent marker: a worker that dies mid-event leaves
``processing`` behind, and after :data:`CLAIM_LEASE` another delivery may take
the claim over. Without that, one crashed worker would strand an event forever
and the card/subscription behind it would never be applied. A FAILED event stays
claimable on purpose — Stripe's retry is the recovery path, and the whole point
of a 5xx is that the next delivery succeeds.

:func:`disposition_for` is pure, so the decision table is tested without a
database; :func:`claim_event` is the atomic implementation it describes.
"""

from __future__ import annotations

import enum
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("scitex")

#: How long a claim is honoured before another delivery may take it over. Well
#: under Stripe's retry schedule, and far longer than any handler here takes.
CLAIM_LEASE = timedelta(minutes=5)


class Disposition(enum.Enum):
    """What a delivery should do with an event it has just been handed."""

    #: Apply it: nobody has, or the last attempt failed, or the claim went stale.
    PROCESS = "process"
    #: Do not apply it: already applied, or another worker holds a live claim.
    SKIP = "skip"


def disposition_for(status: str, *, claimed_at=None, now=None) -> Disposition:
    """The decision table, as a pure function.

    ``claimed_at`` is when the current claim was taken (``updated_at`` on the
    row); it only matters for ``processing``.
    """
    from ..models import BillingEvent

    if status == BillingEvent.Status.PROCESSED:
        return Disposition.SKIP
    if status == BillingEvent.Status.PROCESSING:
        reference = now or timezone.now()
        if claimed_at is not None and reference - claimed_at < CLAIM_LEASE:
            return Disposition.SKIP  # a live worker owns this event
        # Stale claim: the worker that took it never finished. Take it over.
        return Disposition.PROCESS
    return Disposition.PROCESS


def record_event(event) -> tuple[object, bool]:
    """Persist the event if it is new; never touch an existing row's state.

    Returns ``(row, created)``. An existing row is returned UNCHANGED: a retry
    must not reset a processed event back to ``received`` (that is how
    re-application sneaks back in), and must not clear a live claim.
    """
    from ..models import BillingEvent

    return BillingEvent.objects.get_or_create(
        event_id=event.get("id", ""),
        defaults={
            "event_type": event.get("type", ""),
            "payload": event,
        },
    )


def event_disposition(event_id: str) -> Disposition:
    """The disposition for an event that is already recorded.

    An unknown event id is ``PROCESS``: it has not been applied by definition.
    """
    from ..models import BillingEvent

    row = BillingEvent.objects.filter(event_id=event_id).first()
    if row is None:
        return Disposition.PROCESS
    return disposition_for(row.status, claimed_at=row.updated_at)


def claim_event(event_id: str):
    """Atomically take the claim on ``event_id``; ``None`` if someone else has it.

    The read, the decision and the write all happen under a row lock, so two
    concurrent deliveries of the same event cannot both pass. This is the
    function the view calls; it is the only place ``processing`` is entered.
    """
    from ..models import BillingEvent

    with transaction.atomic():
        row = BillingEvent.objects.select_for_update().filter(event_id=event_id).first()
        if row is None:
            return None
        if disposition_for(row.status, claimed_at=row.updated_at) is Disposition.SKIP:
            return None

        fields = ["status", "attempts", "updated_at"]
        row.status = BillingEvent.Status.PROCESSING
        row.attempts = (row.attempts or 0) + 1
        row.save(update_fields=fields)
        return row


def complete_event(row=None, *, event_id: str = "") -> None:
    """Mark the event APPLIED. Idempotent; safe to call twice."""
    from ..models import BillingEvent

    now = timezone.now()
    queryset = (
        BillingEvent.objects.filter(event_id=event_id)
        if row is None
        else BillingEvent.objects.filter(pk=row.pk)
    )
    queryset.update(
        status=BillingEvent.Status.PROCESSED,
        processed_at=now,
        updated_at=now,
        last_error="",
    )


def release_event(error, row=None, *, event_id: str = "") -> None:
    """Mark the claim FAILED so a later delivery may retry it.

    The error text is stored on the row: a poison event is then visible in the
    admin instead of only in a log line nobody reads.
    """
    from ..models import BillingEvent

    now = timezone.now()
    queryset = (
        BillingEvent.objects.filter(event_id=event_id)
        if row is None
        else BillingEvent.objects.filter(pk=row.pk)
    )
    queryset.update(
        status=BillingEvent.Status.FAILED,
        last_error=str(error)[:2000],
        updated_at=now,
    )


__all__ = [
    "CLAIM_LEASE",
    "Disposition",
    "claim_event",
    "complete_event",
    "disposition_for",
    "event_disposition",
    "record_event",
    "release_event",
]
