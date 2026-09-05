#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/__init__.py

"""Keep the develop preview on compute-03 current — ``scitex-hub dev-preview``.

The preview stack (docker compose project ``scitex-hub-dev`` on
``scitex-compute-03``) serves the bind-mounted clone
``/home/ywatanabe/proj/scitex-cloud`` on branch ``develop``. ``runserver``
autoreload and the template watcher make Python / template / CSS edits
live by themselves, but nothing pulled the clone — measured 10 days stale on
2026-09-05. This package is the verb the periodic job
(:mod:`scitex_hub._jobs`) runs every 2 minutes to close that gap.

One tick, in order (:func:`scitex_hub._dev_preview._sync.sync`):

1. take the ``flock`` (a manual run and a timer run never interleave);
2. refuse — and file ONE card per HEAD — unless the clone is a work tree on
   the expected branch with no tracked dirt (an operator's half-finished
   edit must never be clobbered);
3. ``git fetch``; on the first ever run only record HEAD as applied and stop
   (never rebuild the world on the first tick);
4. ``git merge --ff-only origin/develop`` — only when HEAD is an ANCESTOR of
   it; a clone that is ahead of, diverged from, or left behind by a
   rewritten ``origin/develop`` is refused, never force-reset;
5. classify ``applied_head..HEAD`` into the follow-up the change needs
   (:mod:`._classify`), retrying a failed HEAD at most ``max_attempts``
   times before HOLDING it and filing a card — a tick killed mid-action
   (``/usr/bin/timeout``, OOM) counts as one of those attempts;
6. run the follow-up (:mod:`._actions`), wait for the container to report
   healthy, record the new applied HEAD, resolve cards.

Everything is stdlib + click: this runs inside the host supervisor's venv,
NOT inside the Django container, so importing Django here would be both
wrong and heavy.
"""

from __future__ import annotations

from ._actions import ActionFailed, Actions
from ._cards import CardFiler, CliCardFiler
from ._classify import Plan, classify
from ._sync import Config, Outcome, sync

__all__ = [
    "ActionFailed",
    "Actions",
    "CardFiler",
    "CliCardFiler",
    "Config",
    "Outcome",
    "Plan",
    "classify",
    "sync",
]

# EOF
