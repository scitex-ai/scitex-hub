#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-hub auth *`` command group — browser-free credential surface.

Phase-1 PR-5 / card #2 of lead's 7-card backlog. Thin shell over PR #273's
``/api/me/token/`` mint endpoint, complementing PR #274's ``account token``
resource-management verbs.

Per scitex-dev's convention doctrine (msg 548d1e6e), bare top-level
``login`` was rejected as a verb. Lead's card #2 explicitly scopes this
work to the ``auth login`` compound shape (``auth`` group + ``login``
verb), which keeps the polysemy contained inside the ``auth`` subtree
while exposing the user-facing ``scitex-hub auth login`` UX everyone
already expects from cloud CLIs.
"""

from __future__ import annotations

# Verb modules register themselves on import.
from . import _login  # noqa: F401
from ._group import auth

__all__ = ["auth"]

# EOF
