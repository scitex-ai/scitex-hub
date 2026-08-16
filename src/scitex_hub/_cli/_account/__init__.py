#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-hub account *`` command group.

Phase-1 PR-4 of operator-12909's token+CLI surface. Per scitex-dev's
convention doctrine (msg 548d1e6e):

    scitex-hub account token create  → mint a scitex_xxxx APIKey
    scitex-hub account token list    → list tokens
    scitex-hub account token revoke  → revoke a token
    scitex-hub account whoami        → polysemous-leaf identity check
    scitex-hub account doctor        → cached-credential health check

``auth`` was rejected as a noun (not in the catalog); ``login`` was
rejected as a verb (not in the canonical verb set). ``account`` is the
identity noun + ``token <verb>`` reads as resource-management; clean
audit-cli pass shape.
"""

# Verb modules register themselves on import.
from . import (
    _doctor,  # noqa: F401
    _token,  # noqa: F401
    _whoami,  # noqa: F401
)
from ._group import account

__all__ = ["account"]

# EOF
