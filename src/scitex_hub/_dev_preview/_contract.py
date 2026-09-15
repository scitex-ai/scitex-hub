#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_contract.py

"""What one sync tick takes (:class:`Config`) and returns (:class:`Outcome`).

Pure data, kept apart from the engine so the CLI, the tests and the engine
share one definition of the stdout / exit-code contract without importing
the run loop. Also home to the fixed board card ids (one per CAUSE — see
``_cards``) and to :data:`WORST_CASE_TICK_SEC`, the sum every outer timeout
around the tick must exceed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import _actions, _git
from ._actions import Actions
from ._cards import CardFiler, CliCardFiler
from ._classify import Plan

__all__ = [
    "CARD_CLONE_REFUSED",
    "CARD_FETCH_FAILED",
    "CARD_SYNC_FAILED",
    "Config",
    "EXIT_CODES",
    "Outcome",
    "WORST_CASE_TICK_SEC",
]

CARD_CLONE_REFUSED = "hub-dev-preview-clone-refused"
CARD_FETCH_FAILED = "hub-dev-preview-fetch-failed"
CARD_SYNC_FAILED = "hub-dev-preview-sync-failed"

#: Local git plumbing (a handful of 60 s-bounded calls) plus up to a few
#: 60 s-bounded board CLI calls around the budgeted steps.
_LOCAL_SLACK_SEC = 300

#: The longest a tick can legitimately run: every subprocess budget on the
#: worst-case path (fetch, ff-merge, rebuild + health, migrate, npm build)
#: plus the slack above. The job's ``/usr/bin/timeout`` head
#: (``scitex_hub._jobs.HARD_TIMEOUT_SEC``) MUST exceed this — pinned by a
#: test — otherwise the OUTER kill fires before the INNER ones and the
#: recording ``rc=124`` path never runs (measured 2026-09-05: 4800 s of
#: budgets under a 2700 s outer bound).
WORST_CASE_TICK_SEC = (
    _git.FETCH_TIMEOUT_SEC
    + _git.MERGE_TIMEOUT_SEC
    + _actions.REBUILD_TIMEOUT_SEC
    + _actions.HEALTH_TIMEOUT_SEC
    + 2 * _actions.EXEC_TIMEOUT_SEC
    + _LOCAL_SLACK_SEC
)

#: Status -> process exit code; the legend lives in ``_sync``'s docstring.
EXIT_CODES = {
    "ok": 0,
    "noop": 0,
    "already_running": 0,
    "dry_run": 0,
    "failed": 1,
    "refused": 2,
    "held": 3,
}


@dataclass
class Config:
    """Everything one tick needs; the two callables are the test seams."""

    clone: Path
    state_dir: Path
    remote: str = "origin"
    branch: str = "develop"
    container: str = "scitex-hub-dev-django-1"
    dry_run: bool = False
    actions: Actions = field(default_factory=Actions)
    cards: CardFiler = field(default_factory=CliCardFiler)
    max_attempts: int = 2


@dataclass
class Outcome:
    """What one tick did; ``to_json()`` is the stdout contract."""

    status: str
    head_before: str | None = None
    head_after: str | None = None
    plan: Plan | None = None
    actions_run: tuple[str, ...] = ()
    message: str = ""

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.status]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["actions_run"] = list(self.actions_run)
        data["exit_code"] = self.exit_code
        if self.plan is not None:
            data["plan"] = {**asdict(self.plan), "actions": list(self.plan.actions())}
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


# EOF
