#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-hub app *`` command group.

Split into focused modules so each file stays well under the 512-line cap.
The verbs themselves are registered via decorators on the shared ``app``
group defined in :mod:`._group`. Importing this package is enough to wire
all verbs onto the group (each submodule registers on import).
"""

# Verb modules register themselves on import. Order is irrelevant since each
# module decorates a different verb; we import all of them so ``app`` is fully
# populated by the time callers (e.g. main.py) reach for it.
from . import (
    _create,  # noqa: F401
    _deps,  # noqa: F401
    _inventory,  # noqa: F401
    _prefs,  # noqa: F401
    _scaffold,  # noqa: F401
)
from ._group import app

__all__ = ["app"]

# EOF
