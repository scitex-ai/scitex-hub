#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_state.py

"""Regenerable on-disk state and the JSONL log of the preview sync.

Layout (mirrors scitex-dev's ``~/.scitex/<package>/runtime/`` convention,
``scitex_dev.jobs._logsink``: 1 MiB rotation to ``<log>.1``)::

    ~/.scitex/hub/runtime/dev-preview-sync/
        state.json   applied_head / per-HEAD attempts / fetch failures / cards
        sync.log     one JSON object per line, one line per step
        lock         flock target (see _lock.py)

WHY THE JOB KEEPS ITS OWN LOG
-----------------------------
The supervisor discards the job's stdout (0.56.3) or logs a tail only on
failure (0.59.0). A job that fires every 2 minutes and mostly says "noop"
needs a place where "what happened at 03:14" is answerable without
guessing, and a place that does not grow without bound — hence JSONL and
the 1 MiB rotation.

WHY THE STATE IS REGENERABLE
----------------------------
Everything here can be rebuilt from the clone and the board: delete the
directory and the next tick records HEAD as applied and carries on. That is
also why a CORRUPT ``state.json`` is moved aside (``state.json.corrupt-<ts>``)
and logged rather than raised on every tick forever — an unattended job that
can never self-heal from one bad write is worse than one that restarts from
"treat HEAD as applied", which is the safe first-run behaviour anyway.

WHY ATTEMPTS ARE WRITTEN AHEAD
------------------------------
The job runs under ``/usr/bin/timeout`` (and can be OOM-killed or rebooted);
a SIGTERM lands with no Python frame to catch it in unless a handler is
installed, and even the handler cannot run after SIGKILL. Reproduced on
2026-09-05: a tick killed mid-rebuild left ``attempts`` EMPTY, so the retry
gate never tripped and the same rebuild was restarted every tick with no
card. So the engine records the attempt (``rc`` = :data:`RC_KILLED`)
BEFORE the first action starts and only clears it on success — a tick that
dies mid-way still counts, whatever killed it.

WHY FETCH FAILURES LIVE APART FROM ACTION ATTEMPTS
--------------------------------------------------
``attempts`` is keyed by HEAD; a fetch failure says nothing about that HEAD
(the network is down, not the commit). Recording it under the same key
overwrote a real rebuild failure, granted an extra rebuild attempt and made
the held card blame the fetch (probe K, 2026-09-05). ``fetch_failures`` is
therefore its own record, cleared by the first fetch that succeeds.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "LOG_ROTATE_BYTES",
    "RC_KILLED",
    "State",
    "append_log",
    "load_state",
    "save_state",
    "utc_now",
]

#: Same threshold scitex-dev's log sink uses for every federated job.
LOG_ROTATE_BYTES = 1_048_576

#: The ``rc`` an attempt carries while its action is IN FLIGHT. If the tick
#: dies before the action returns (``/usr/bin/timeout``'s SIGTERM, OOM,
#: reboot) this is what the next tick reads — subprocess's "killed by
#: SIGTERM" convention (negative signal number), so a human reading
#: ``state.json`` recognises it. Non-zero on purpose: ``failure_count``
#: treats ``rc == 0`` as "not a failure".
RC_KILLED = -15

_STATE_FILE = "state.json"
_LOG_FILE = "sync.log"


def utc_now() -> str:
    """ISO-8601 UTC timestamp with seconds, e.g. ``2026-09-05T03:14:07Z``."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class State:
    """What the sync remembers between ticks.

    ``applied_head`` — the commit whose follow-up actions have COMPLETED
    (or that was recorded as the baseline on the first run). ``None`` only
    before the first run.
    ``attempts`` — ``{head: {"action", "rc", "count", "ts"}}``: the last
    failed (or in-flight) action at that HEAD and how many ticks have
    failed there; the retry gate reads ``count``.
    ``fetch_failures`` — ``{"rc", "count", "ts"}`` while ``git fetch`` keeps
    failing, ``{}`` otherwise. Kept apart from ``attempts`` (see the module
    docstring).
    ``filed_cards`` — ``{card_id: head}``: which HEAD each board card was
    filed for, so a card is filed once per HEAD and resolved once fixed.
    """

    applied_head: str | None = None
    attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    fetch_failures: dict[str, Any] = field(default_factory=dict)
    filed_cards: dict[str, str] = field(default_factory=dict)

    def record_attempt(self, head: str, action: str, rc: int) -> int:
        """Bump the failure count for ``head`` and return the new count.

        Called ONCE per tick, before the first action starts (write-ahead,
        with ``rc=RC_KILLED``), or when a non-action step at ``head`` fails.
        """
        previous = self.attempts.get(head, {})
        count = int(previous.get("count", 0)) + 1
        self.attempts[head] = {
            "action": action,
            "rc": rc,
            "count": count,
            "ts": utc_now(),
        }
        return count

    def update_attempt(self, head: str, action: str, rc: int) -> int:
        """Rewrite WHICH action and rc the current attempt at ``head`` carries.

        The count is untouched: one tick is one attempt however many of its
        actions ran before one failed. Returns the count.
        """
        entry = self.attempts.setdefault(head, {"count": 1})
        entry.update({"action": action, "rc": rc, "ts": utc_now()})
        return int(entry["count"])

    def failure_count(self, head: str) -> int:
        """How many consecutive failures ``head`` has accumulated (0 if none)."""
        entry = self.attempts.get(head)
        if not entry or int(entry.get("rc", 0)) == 0:
            return 0
        return int(entry.get("count", 0))

    def record_fetch_failure(self, rc: int) -> int:
        """Bump the consecutive-fetch-failure count and return it."""
        count = int(self.fetch_failures.get("count", 0)) + 1
        self.fetch_failures = {"rc": rc, "count": count, "ts": utc_now()}
        return count


def load_state(state_dir: Path) -> tuple[State, str | None]:
    """Read ``state.json``; returns ``(state, note)``.

    ``note`` is ``None`` normally, or a sentence describing why a fresh
    state was returned instead (missing file is silent; a corrupt file is
    moved aside and reported so the caller can log it).
    """
    path = state_dir / _STATE_FILE
    if not path.exists():
        return State(), None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"top-level JSON is {type(raw).__name__}, not an object")
        return (
            State(
                applied_head=raw.get("applied_head"),
                attempts=dict(raw.get("attempts") or {}),
                fetch_failures=dict(raw.get("fetch_failures") or {}),
                filed_cards=dict(raw.get("filed_cards") or {}),
            ),
            None,
        )
    except (OSError, ValueError) as exc:
        aside = path.with_name(
            f"{_STATE_FILE}.corrupt-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        )
        try:
            os.replace(path, aside)
            moved = f"moved aside to {aside.name}"
        except OSError as move_exc:
            moved = f"could not move aside: {move_exc}"
        return State(), f"state.json unreadable ({exc}); {moved}; starting fresh"


def save_state(state_dir: Path, state: State) -> None:
    """Atomically write ``state.json`` (tmp file + ``os.replace``)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / _STATE_FILE
    tmp = target.with_name(f".{_STATE_FILE}.{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp, target)


def append_log(state_dir: Path, record: dict[str, Any]) -> None:
    """Append one JSON object to ``sync.log``, rotating at 1 MiB.

    ``ts`` is stamped here unless the caller already set it. Rotation is a
    single rename to ``sync.log.1`` (the previous ``.1`` is dropped) —
    exactly what scitex-dev's ``rotate_if_large`` does for every other job.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    log = state_dir / _LOG_FILE
    try:
        if log.is_file() and log.stat().st_size > LOG_ROTATE_BYTES:
            os.replace(log, log.with_name(f"{_LOG_FILE}.1"))
    except OSError:
        # A failed rotation must not lose the record that follows; the
        # file just grows past the threshold until the next tick retries.
        pass
    line = json.dumps({"ts": utc_now(), **record}, sort_keys=True, default=str)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# EOF
