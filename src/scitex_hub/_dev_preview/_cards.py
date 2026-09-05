#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_cards.py

"""Surface a stuck preview on the fleet board (scitex-cards), best effort.

WHY A CARD AND NOT JUST A LOG LINE
----------------------------------
The sync runs unattended every 2 minutes with its stdout discarded. When it
cannot proceed — the clone has an operator's uncommitted edit, the clone is
not on ``origin/develop``, the fetch keeps failing, or a rebuild failed
twice — the only thing that reaches a human is what lands on the board.
Three cards, fixed ids so each is filed ONCE per HEAD and resolved when its
condition clears; one id per CAUSE, because a card that could mean two
different things cannot be resolved by the recovery of one of them:

* ``hub-dev-preview-clone-refused`` (blocker ``operator-decision``): the
  clone needs a human — stash / commit / reset it.
* ``hub-dev-preview-fetch-failed`` (blocker ``dependency``): ``git fetch``
  failed ``max_attempts`` ticks in a row; resolved by the first fetch that
  succeeds, whether or not anything new arrived.
* ``hub-dev-preview-sync-failed`` (blocker ``dependency``): an action failed
  ``max_attempts`` times at one HEAD; the preview is HELD at the previous
  HEAD until someone reads ``sync.log`` and fixes the cause.

BEST EFFORT, BY DESIGN — BUT HONEST ABOUT IT
--------------------------------------------
The board is a side channel. A board outage, a missing ``scitex-cards``
binary or a schema change in its CLI must never turn a working sync into a
failing one — so every failure here is LOGGED through the injected ``log``
callable and swallowed; nothing in this module raises to the caller. Each
verb does RETURN whether the board accepted the write, and the engine only
remembers a card as filed / resolved when it did: before 2026-09-05 a board
outage during the one tick that files a card was recorded as "filed" and
the card was never retried for that HEAD.

:class:`CardFiler` is a ``Protocol`` so the sync engine can be driven by a
recording filer in tests without a mock library; :class:`NullCardFiler` is
the ``--no-cards`` adapter that only logs, for manual runs against a clone
whose refusals must not land on the operator's real board.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Protocol

from scitex_hub._jobs import PREVIEW_HOST

__all__ = ["CardFiler", "CliCardFiler", "NullCardFiler"]

_CARDS_TIMEOUT = 60

LogFn = Callable[[dict[str, Any]], None]


class CardFiler(Protocol):
    """What the sync engine needs from a board adapter.

    Both verbs return True only when the board ACCEPTED the write; the engine
    retries an unaccepted one on the next tick instead of remembering it.
    """

    def file_blocked(self, card_id: str, title: str, note: str, blocker: str) -> bool:
        """Create or re-block ``card_id`` with ``note``; never raises."""

    def resolve(self, card_id: str, note: str) -> bool:
        """Mark ``card_id`` done with ``note``; never raises."""


class NullCardFiler:
    """The ``--no-cards`` adapter: log what WOULD be filed, touch no board.

    Returns False so the engine does not remember the card as filed — a
    later run WITH cards still files it for the same HEAD.
    """

    def __init__(self, *, log: LogFn | None = None) -> None:
        self._log = log or (lambda record: None)

    def file_blocked(self, card_id: str, title: str, note: str, blocker: str) -> bool:
        self._log(
            {
                "step": "cards",
                "ok": False,
                "card": card_id,
                "action": "file_blocked",
                "detail": "skipped (--no-cards)",
            }
        )
        return False

    def resolve(self, card_id: str, note: str) -> bool:
        self._log(
            {
                "step": "cards",
                "ok": False,
                "card": card_id,
                "action": "resolve",
                "detail": "skipped (--no-cards)",
            }
        )
        return False


def _default_binary() -> str | None:
    sibling = Path(sys.executable).with_name("scitex-cards")
    if sibling.is_file():
        return str(sibling)
    return shutil.which("scitex-cards")


class CliCardFiler:
    """Board adapter over the ``scitex-cards`` CLI (flags verified 2026-09-05, v0.50.0)."""

    def __init__(
        self,
        *,
        binary: str | None = None,
        log: LogFn | None = None,
        assignee: str = "scitex-hub",
        project: str = "scitex-hub",
        host: str = PREVIEW_HOST,
        priority: int = 2,
    ) -> None:
        self.binary = binary if binary is not None else _default_binary()
        self._log = log or (lambda record: None)
        self.assignee = assignee
        self.project = project
        self.host = host
        self.priority = priority

    # -- plumbing ---------------------------------------------------------
    def _run(self, *args: str) -> subprocess.CompletedProcess[str] | None:
        if not self.binary:
            self._log(
                {
                    "step": "cards",
                    "ok": False,
                    "detail": "scitex-cards binary not found",
                }
            )
            return None
        argv = [self.binary, *args]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=_CARDS_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._log({"step": "cards", "ok": False, "argv": argv, "detail": str(exc)})
            return None
        if completed.returncode != 0:
            self._log(
                {
                    "step": "cards",
                    "ok": False,
                    "argv": argv,
                    "rc": completed.returncode,
                    "detail": (completed.stderr or completed.stdout).strip()[-500:],
                }
            )
            return None
        return completed

    def _exists(self, card_id: str) -> bool:
        completed = self._run(
            "list-tasks", "--id-prefix", card_id, "--scope", "", "--json"
        )
        if completed is None:
            return False
        try:
            rows = json.loads(completed.stdout or "[]")
        except ValueError as exc:
            self._log(
                {
                    "step": "cards",
                    "ok": False,
                    "detail": f"list-tasks JSON unreadable: {exc}",
                }
            )
            return False
        return any(isinstance(row, dict) and row.get("id") == card_id for row in rows)

    # -- CardFiler ----------------------------------------------------------
    def file_blocked(self, card_id: str, title: str, note: str, blocker: str) -> bool:
        """Create the card blocked, or re-block an existing one and comment."""
        if self._exists(card_id):
            updated = self._run(
                "update",
                card_id,
                "--status",
                "blocked",
                "--blocker",
                blocker,
                "--note",
                note,
            )
            commented = self._run("comment", card_id, note) if updated else None
            ok = bool(updated and commented)
        else:
            ok = (
                self._run(
                    "add",
                    card_id,
                    title,
                    "--status",
                    "blocked",
                    "--blocker",
                    blocker,
                    "--assignee",
                    self.assignee,
                    "--scope",
                    f"agent:{self.assignee}",
                    "--project",
                    self.project,
                    "--host",
                    self.host,
                    "--priority",
                    str(self.priority),
                    "--note",
                    note,
                )
                is not None
            )
        self._log(
            {"step": "cards", "ok": ok, "card": card_id, "action": "file_blocked"}
        )
        return ok

    def resolve(self, card_id: str, note: str) -> bool:
        """Flip the card to done, clear the blocker, leave the reason as a comment."""
        updated = self._run("update", card_id, "--status", "done", "--blocker", "none")
        commented = self._run("comment", card_id, note) if updated else None
        ok = bool(updated and commented)
        self._log({"step": "cards", "ok": ok, "card": card_id, "action": "resolve"})
        return ok


# EOF
