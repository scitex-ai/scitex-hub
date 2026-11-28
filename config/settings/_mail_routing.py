#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_mail_routing.py
"""Parse the env-configured recipient lists for the Hub's ops mail.

``ADMINS`` / ``MANAGERS`` used to be a literal in settings_shared naming the
operator's personal inbox, so every Django error mail landed there. On
2026-11-27 the operator ruled that system/ops alerts go to a dedicated address
(``branding.OPS_ALERT_EMAIL``, dev@) and that the list is configurable per
deployment. This module is the one parser for that list, kept free of Django
imports so the settings gate tests can load it by path.

Accepted value: a comma-separated list of ``addr`` or ``Name <addr>`` entries,
for example ``dev@scitex.ai`` or ``Ops <dev@scitex.ai>, oncall@example.org``.
"""

from __future__ import annotations

from email.utils import getaddresses


def parse_address_list(value: str, setting: str) -> list[tuple[str, str]]:
    """Return Django's ``[(name, address), ...]`` for a comma-separated list.

    Fails loudly on an entry without an ``@``: a typo here would build the
    handler with a recipient that bounces, and an alert rail that bounces is
    indistinguishable, from the operator's side, from one that never fires.
    An EMPTY value is refused for the same reason -- unset the variable to get
    the default instead.
    """
    entries = [part.strip() for part in (value or "").split(",") if part.strip()]
    if not entries:
        raise ValueError(
            f"{setting} is set but empty. Unset it to use the default "
            "ops-alert address, or list at least one recipient."
        )
    parsed: list[tuple[str, str]] = []
    for entry in entries:
        ((name, address),) = getaddresses([entry]) or [("", "")]
        if "@" not in address or any(c in entry for c in "\r\n"):
            raise ValueError(
                f"{setting}: {entry!r} is not an email address. Use "
                "'addr' or 'Name <addr>', comma-separated."
            )
        parsed.append((name or address, address))
    return parsed


# EOF
