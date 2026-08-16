#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/account/__init__.py
"""SciTeX Hub account namespace — Python parity for the ``account`` CLI tree.

Mirrors the ``scitex-hub account`` CLI verbs as a thin importable surface so
agent-programmatic callers don't have to shell out:

    >>> import scitex_hub
    >>> scitex_hub.account.whoami.whoami()
    {'username': 'ywatanabe', 'email': 'ywatanabe@scitex.ai'}
    >>> scitex_hub.account.token.create(name="cli", scopes=["publish"])
    {'token': 'scitex_...', 'prefix': '...', 'scopes': ['publish']}

Card #3 chunk 1 (PR ``feat/hub-python-api-parity``): only ``token`` and
``whoami`` ship in this slot. The remaining sub-trees (``gitea``,
``docker``, ``mcp``) follow in later chunks.

Each function thin-wraps the HTTP call to ``/api/me/...`` and reuses the
:func:`scitex_hub._mcp_tools.api._make_request` transport so the
``SCITEX_HUB_URL`` / ``SCITEX_HUB_IS_ON_SITE`` resolution stays
single-sourced.
"""

from __future__ import annotations

from . import token as token
from . import whoami as whoami

__all__ = ["token", "whoami"]

# EOF
