#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/settings_email.py
"""Outgoing mail: SMTP transport, senders and ops-alert recipients.

Split out of settings_shared (which star-imports it at the same point, so the
override order of every environment module is unchanged).

Mail-routing policy, decided by the operator on 2026-11-27 after his inbox was
flooded with Django error mail (the table lives in config/branding.py and
docs/ops/mail-routing.md):

* system/ops alerts -- ADMINS/MANAGERS error mail, the site-down and flood
  alarms -- go From ``SERVER_EMAIL`` (no-reply@) To ``ADMINS`` (dev@);
* user-facing mail goes From ``DEFAULT_FROM_EMAIL`` (no-reply@) To the user.

Environment keys (all optional; defaults follow the policy):

- ``SCITEX_HUB_ADMINS``             comma-separated "addr" / "Name <addr>"
                                    (default: branding.OPS_ALERT_EMAIL)
- ``SCITEX_HUB_MANAGERS``           same format (default: ADMINS)
- ``SCITEX_HUB_DEFAULT_FROM_EMAIL`` (default: branding.NOREPLY_EMAIL)
- ``SCITEX_HUB_SERVER_EMAIL``       (default: branding.NOREPLY_EMAIL)
- ``SCITEX_HUB_ADMIN_MAIL_REPEAT_WINDOW_SECONDS`` see settings_logging
"""

from config import branding
from config._env import getenv_with_legacy_alias as _getenv_alias

from ._mail_routing import parse_address_list as _parse_address_list

EMAIL_BACKEND = _getenv_alias("SCITEX_HUB_EMAIL_BACKEND")
EMAIL_HOST = _getenv_alias("SCITEX_HUB_EMAIL_HOST")
EMAIL_PORT = int(_getenv_alias("SCITEX_HUB_EMAIL_PORT", "587") or "587")
EMAIL_USE_TLS = (
    _getenv_alias("SCITEX_HUB_EMAIL_USE_TLS", "True") or "True"
).lower() == "true"
EMAIL_HOST_USER = _getenv_alias("SCITEX_HUB_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _getenv_alias("SCITEX_HUB_EMAIL_HOST_PASSWORD")
# Fail fast, never hang the request: without this Django SMTP blocks
# indefinitely on a stalled mail server (observed: signup POST never
# returned). The signup view already handles send failure gracefully.
EMAIL_TIMEOUT = int(_getenv_alias("SCITEX_HUB_EMAIL_TIMEOUT", "10") or "10")
# Explicit senders. They used to be EMAIL_HOST_USER implicitly, which made
# "who is this mail from" a side effect of whichever SMTP login the env file
# happened to hold.
DEFAULT_FROM_EMAIL = _getenv_alias(
    "SCITEX_HUB_DEFAULT_FROM_EMAIL", branding.NOREPLY_EMAIL
)
SERVER_EMAIL = _getenv_alias("SCITEX_HUB_SERVER_EMAIL", branding.NOREPLY_EMAIL)

# Recipients of the mail_admins logging handler (settings_logging). Defined
# HERE, once, rather than per environment: it lived only in settings_prod
# until 2026-08-15, which meant staging constructed the handler, passed every
# check a grep could make, and delivered to nobody because ADMINS was the
# empty default. require_debug_false already keeps this off dev machines, so
# the environment gate does not need a second, silent one.
#
# The default is the ops address, NOT the operator's personal inbox (policy
# above). It is never empty: the parser refuses an empty or malformed list.
ADMINS = _parse_address_list(
    _getenv_alias("SCITEX_HUB_ADMINS", branding.OPS_ALERT_EMAIL),
    "SCITEX_HUB_ADMINS",
)
_managers_override = _getenv_alias("SCITEX_HUB_MANAGERS")
MANAGERS = (
    _parse_address_list(_managers_override, "SCITEX_HUB_MANAGERS")
    if _managers_override is not None
    else list(ADMINS)
)


# EOF
