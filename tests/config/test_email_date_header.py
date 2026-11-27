#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_email_date_header.py
"""Every mail Django sends must carry a Date header that names the true instant.

Prod, 2026-11-27: signup verification mail and ADMINS error mail arrived dated
"03:11 +00:00" when they were sent at 12:11Z -- 9 h early, in a JST setting.
Django 5.2 with ``EMAIL_USE_LOCALTIME = False`` writes the date with the RFC
5322 ``-0000`` zone ("offset unknown"); ``email.utils.parsedate_to_datetime``
returns a naive datetime for that, and a reader that localises it to Asia/Tokyo
moves the instant back 9 h.

The assertions are reader-independent: the header must parse to a
timezone-AWARE datetime equal to the moment the message was built, whatever
TIME_ZONE is and whatever the process-local zone is. Uses the hub's real
settings (no override of the mail setting under test) and Django's real
message builder.
"""

from __future__ import annotations

import datetime as dt
from email.utils import parsedate_to_datetime
from typing import NamedTuple

import pytest
from django.core import mail
from django.core.mail import EmailMessage, mail_admins
from django.test import override_settings

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
TIME_ZONES = ["UTC", "Asia/Tokyo", "America/Los_Angeles"]
# The header has whole-second resolution.
ONE_SECOND = dt.timedelta(seconds=1)


class SentDate(NamedTuple):
    header: str
    before: dt.datetime
    after: dt.datetime


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _build_plain_message() -> str:
    email = EmailMessage("subject", "body", "no-reply@example.com", ["u@example.com"])
    return email.message()["Date"]


def _send_admin_error_mail() -> str:
    mail.outbox = []
    mail_admins("probe", "body")
    return mail.outbox[0].message()["Date"]


@pytest.fixture(
    params=[
        (source, zone)
        for source in (_build_plain_message, _send_admin_error_mail)
        for zone in TIME_ZONES
    ],
    ids=lambda p: f"{p[0].__name__.strip('_')}-{p[1]}",
)
def sent_date(request) -> SentDate:
    """Date header of a message built under TIME_ZONE, bracketed by real time.

    override_settings(TIME_ZONE=...) also re-points the process TZ (Django's
    setting_changed handler calls time.tzset), as a deployment would.
    """
    source, zone = request.param
    with override_settings(TIME_ZONE=zone, EMAIL_BACKEND=LOCMEM):
        before = _utc_now()
        header = source()
        after = _utc_now()
    return SentDate(header, before, after)


def test_date_header_carries_an_explicit_utc_offset(sent_date):
    # Arrange
    header = sent_date.header

    # Act
    parsed = parsedate_to_datetime(header)

    # Assert
    assert parsed.tzinfo is not None, (
        f"Date {header!r} has no usable offset (RFC 5322 '-0000'); "
        "readers interpret it as local wall-clock time"
    )


def test_date_header_names_the_send_instant(sent_date):
    # Arrange
    lo = sent_date.before.replace(microsecond=0)
    hi = sent_date.after + ONE_SECOND

    # Act
    parsed = parsedate_to_datetime(sent_date.header)
    as_utc = parsed.astimezone(dt.timezone.utc)

    # Assert
    assert lo <= as_utc <= hi, (
        f"Date {sent_date.header!r} reads as {as_utc}, not the send instant "
        f"({sent_date.before} .. {sent_date.after})"
    )


# EOF
