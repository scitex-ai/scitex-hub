#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_sync.py

"""One tick of the develop-preview sync: fetch, fast-forward, classify, act.

This module states the contract and owns the lock and the SIGTERM handler;
the nine steps live in :mod:`._tick`, the data in :mod:`._contract`.

STATUSES AND EXIT CODES (what the supervisor's failure log will show)
--------------------------------------------------------------------
``ok``               0  actions ran and the preview is at the new HEAD
``noop``             0  nothing to do (up to date, autoreload-only change,
                        or the first run recording its baseline)
``already_running``  0  another sync holds the lock — not an error
``dry_run``          0  the plan was computed and printed, nothing moved
``failed``           1  an action or the fetch failed, or the tick was
                        killed mid-action; will retry next tick
``refused``          2  the clone needs a human (dirty / wrong branch / not
                        on origin/develop / not a work tree); card filed
                        once per HEAD
``held``             3  ``max_attempts`` failures at this HEAD; the preview
                        stays at the previous HEAD until someone intervenes;
                        card filed once per HEAD

Only ``failed`` is retried automatically, and only ``max_attempts`` times:
a rebuild that fails deterministically must not be re-run every 2 minutes
for the rest of the day. Held and refused both wait for a human and say so
on the board.

EVERY WAY A TICK CAN DIE MID-ACTION COUNTS AS AN ATTEMPT
--------------------------------------------------------
The retry gate is only as good as the failures it sees. Three ways a failed
action used to leave ``attempts`` untouched — and therefore re-ran the same
rebuild on every tick with nothing on the board (all reproduced 2026-09-05):

* the job's outer ``/usr/bin/timeout`` SIGTERMed the tick while a
  slow-but-alive rebuild was running (the inner budgets summed to more than
  the outer bound) — no Python frame caught it;
* an action raised something other than :class:`ActionFailed`
  (``health_status`` let ``FileNotFoundError`` for a missing ``docker`` and
  ``TimeoutExpired`` escape);
* a diff failure returned before the gate.

So: the attempt is WRITTEN AHEAD (``rc=RC_KILLED``) and saved before the
first action starts, and only cleared on success; a SIGTERM handler turns
the signal into an exception the act loop records with the real signal
number; the act loop catches ``Exception`` after ``ActionFailed``; the diff
failure goes through the same gate; and the outer bound
(``scitex_hub._jobs.HARD_TIMEOUT_SEC``) must exceed
:data:`WORST_CASE_TICK_SEC` so the inner, recording timeouts fire first.

THE CLONE MUST BE ON origin/develop, NOT MERELY RELATED TO IT
-------------------------------------------------------------
HEAD is accepted in exactly two shapes: equal to ``origin/develop`` (up to
date, or resuming after a failed action), or a strict ANCESTOR of it (a
fast-forward). Anything else — a local commit on top, a genuine divergence,
or an ``origin/develop`` that was force-pushed BACKWARDS so the clone is now
ahead of it — is refused with a card, never force-reset and never quietly
reported as "up to date" while the preview serves a commit that is no
longer on develop.

THE FIRST RUN NEVER REBUILDS THE WORLD
--------------------------------------
With no ``applied_head`` on record, this tick records HEAD as applied and
stops. Otherwise the very first tick after install would diff against
nothing and could decide that every Dockerfile in history "changed". An
``applied_head`` the clone does not HAVE (state from another clone, a
re-clone, a hand reset after a rewritten origin) is treated the same way,
loudly: it is logged and HEAD becomes the new baseline, because a diff
against a commit that does not exist would otherwise fail on every tick
forever.

DRY RUN
-------
``--dry-run`` fetches (a remote-tracking update is harmless and is the only
way to know what WOULD merge), then computes the plan for
``applied_head..origin/develop`` without merging, acting, saving state or
filing cards — and says ``would REFUSE`` when the real tick would.
"""

from __future__ import annotations

from pathlib import Path

from ._contract import (
    CARD_CLONE_REFUSED,
    CARD_FETCH_FAILED,
    CARD_SYNC_FAILED,
    WORST_CASE_TICK_SEC,
    Config,
    Outcome,
)
from ._lock import AlreadyRunning, hold_lock
from ._signals import TickInterrupted, signum_of, sigterm_raises
from ._state import append_log
from ._tick import Tick

__all__ = [
    "CARD_CLONE_REFUSED",
    "CARD_FETCH_FAILED",
    "CARD_SYNC_FAILED",
    "Config",
    "Outcome",
    "WORST_CASE_TICK_SEC",
    "sync",
]


def sync(config: Config) -> Outcome:
    """Run one tick under the lock; see the module docstring for the contract."""
    state_dir = Path(config.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        with hold_lock(state_dir), sigterm_raises():
            return Tick(config).run()
    except AlreadyRunning as exc:
        append_log(state_dir, {"step": "already_running", "detail": str(exc)})
        return Outcome("already_running", message=str(exc))
    except (TickInterrupted, KeyboardInterrupt) as exc:
        # Killed outside the act loop (fetch / merge / plumbing): nothing to
        # record — the next tick simply redoes those steps.
        signum = signum_of(exc)
        message = f"killed by signal {signum} outside an action; nothing recorded"
        append_log(state_dir, {"step": "killed", "signal": signum, "detail": message})
        return Outcome("failed", message=message)


# EOF
