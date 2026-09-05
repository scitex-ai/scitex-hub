#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_tick.py

"""The run loop of one locked sync tick (:class:`Tick`).

:mod:`._sync` states the contract and owns the lock and the signal handler;
this module is the nine numbered steps under them — preconditions, fetch,
baseline, dry run, refuse / resume / fast-forward, classify, retry gate,
act, success. Each step that can fail says how it is recorded, because the
retry gate is only as good as the failures it sees (every gap found on
2026-09-05 was a failure path that returned before recording anything).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _git
from ._actions import ActionFailed
from ._classify import Plan, classify
from ._contract import (
    CARD_CLONE_REFUSED,
    CARD_FETCH_FAILED,
    CARD_SYNC_FAILED,
    Config,
    Outcome,
)
from ._signals import TickInterrupted, signum_of
from ._state import RC_KILLED, append_log, load_state, save_state

__all__ = ["Tick"]


class Tick:
    """The mutable working set of one locked run; ``run()`` is the tick."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.clone = Path(config.clone)
        self.state_dir = Path(config.state_dir)
        self.state, note = load_state(self.state_dir)
        if note:
            self.log("state", ok=False, detail=note)

    # -- helpers ------------------------------------------------------------
    def log(self, step: str, **detail: Any) -> None:
        append_log(self.state_dir, {"step": step, **detail})

    def save(self) -> None:
        if not self.config.dry_run:
            save_state(self.state_dir, self.state)

    def file_card_once(
        self, card_id: str, head: str, title: str, note: str, blocker: str
    ) -> None:
        """File ``card_id`` for ``head`` unless the board already accepted it.

        Only an ACCEPTED write is remembered: after a board outage the next
        tick tries again instead of believing the card exists.
        """
        if self.config.dry_run:
            self.log("cards", ok=True, card=card_id, action="would_file", head=head)
            return
        if self.state.filed_cards.get(card_id) == head:
            return
        accepted = bool(self.config.cards.file_blocked(card_id, title, note, blocker))
        if accepted:
            self.state.filed_cards[card_id] = head
        self.log(
            "cards",
            ok=accepted,
            card=card_id,
            action="filed" if accepted else "file_failed",
            head=head,
        )

    def resolve_card(self, card_id: str, note: str) -> None:
        if self.config.dry_run or card_id not in self.state.filed_cards:
            return
        accepted = bool(self.config.cards.resolve(card_id, note))
        if accepted:
            del self.state.filed_cards[card_id]
        self.log(
            "cards",
            ok=accepted,
            card=card_id,
            action="resolved" if accepted else "resolve_failed",
        )

    def refuse(self, reason: str, head: str | None) -> Outcome:
        self.log("refused", head=head, detail=reason)
        self.file_card_once(
            CARD_CLONE_REFUSED,
            head or "unknown",
            "[dev-preview] clone refused: the develop preview is not being updated",
            f"{reason}\nclone: {self.clone}\nHEAD: {head or 'unknown'}\n"
            f"Fix the clone (stash/commit/reset), the next tick resumes by itself.",
            "operator-decision",
        )
        self.save()
        return Outcome("refused", head_before=head, head_after=head, message=reason)

    def hold(self, head_before: str, head_after: str, plan: Plan | None) -> Outcome:
        """``max_attempts`` failures at ``head_after``: stop retrying, file the card."""
        last = self.state.attempts[head_after]
        rc = int(last["rc"])
        cause = (
            "killed mid-action (timeout / signal)" if rc == RC_KILLED else f"rc={rc}"
        )
        applied = self.state.applied_head or "unknown"
        message = (
            f"held at {head_after[:12]}: {last['action']} failed {last['count']}x "
            f"(last {cause}); preview stays at {applied[:12]}"
        )
        self.log("held", head=head_after, detail=message)
        self.file_card_once(
            CARD_SYNC_FAILED,
            head_after,
            "[dev-preview] sync failed: preview held at previous commit",
            f"{message}\nclone: {self.clone}\nlog: {self.state_dir / 'sync.log'}\n"
            f"Fix the cause, then clear attempts in state.json or push a new commit.",
            "dependency",
        )
        self.save()
        return Outcome(
            "held",
            head_before=head_before,
            head_after=head_after,
            plan=plan,
            message=message,
        )

    def action_failed(
        self,
        *,
        head_before: str,
        head_after: str,
        plan: Plan,
        ran: list[str],
        action: str,
        rc: int,
        tail: str,
        message: str,
        phase: str = "failed",
    ) -> Outcome:
        """Settle the write-ahead attempt with what actually went wrong."""
        count = self.state.update_attempt(head_after, action, rc)
        self.log(
            "action",
            name=action,
            head=head_after,
            phase=phase,
            rc=rc,
            count=count,
            tail=tail,
        )
        self.save()
        return Outcome(
            "failed",
            head_before=head_before,
            head_after=head_after,
            plan=plan,
            actions_run=tuple(ran),
            message=message,
        )

    # -- the tick -----------------------------------------------------------
    def run(self) -> Outcome:
        cfg = self.config
        # 1. preconditions — an operator's half-finished edit is never clobbered
        if not _git.is_work_tree(self.clone):
            return self.refuse(f"{self.clone} is not a git work tree", None)
        head_before = _git.head(self.clone)
        branch = _git.current_branch(self.clone)
        if branch != cfg.branch:
            return self.refuse(
                f"clone is on {branch!r}, expected {cfg.branch!r}", head_before
            )
        dirt = _git.tracked_dirt(self.clone)
        if dirt:
            return self.refuse(
                f"tracked files are modified ({len(dirt)}): {'; '.join(dirt[:5])}",
                head_before,
            )

        # 2. fetch — the only network step; its failures are tracked apart
        #    from per-HEAD action attempts (see _state)
        try:
            _git.fetch(self.clone, cfg.remote, cfg.branch)
        except _git.GitError as exc:
            count = self.state.record_fetch_failure(exc.returncode)
            self.log(
                "fetch", ok=False, rc=exc.returncode, count=count, detail=exc.stderr
            )
            if count >= cfg.max_attempts:
                self.file_card_once(
                    CARD_FETCH_FAILED,
                    head_before,
                    "[dev-preview] sync failed: fetch keeps failing",
                    f"git fetch {cfg.remote} {cfg.branch} failed {count}x in a row.\n"
                    f"last stderr: {exc.stderr[-500:]}\nclone: {self.clone}",
                    "dependency",
                )
            self.save()
            return Outcome(
                "failed",
                head_before=head_before,
                head_after=head_before,
                message=str(exc),
            )
        if self.state.fetch_failures:
            self.state.fetch_failures = {}
            self.resolve_card(CARD_FETCH_FAILED, "fetch recovered")
            self.save()
        self.log("fetch", ok=True)

        # 3. baseline: the first run, or an applied_head this clone does not have
        applied = self.state.applied_head
        if applied is not None and not _git.is_commit(self.clone, applied):
            self.log(
                "state",
                ok=False,
                detail=(
                    f"applied_head {applied} is unknown to this clone (re-clone or "
                    f"hand reset?); re-recording {head_before} as the baseline"
                ),
            )
            self.state.applied_head = None
            self.state.attempts.clear()
        if self.state.applied_head is None:
            message = f"first run: recorded {head_before[:12]} as applied; nothing done"
            if cfg.dry_run:
                self.log("dry_run", detail=message)
                return Outcome(
                    "dry_run",
                    head_before=head_before,
                    head_after=head_before,
                    message=message,
                )
            self.state.applied_head = head_before
            self.save()
            self.log("first_run", head=head_before)
            return Outcome(
                "noop", head_before=head_before, head_after=head_before, message=message
            )

        origin_ref = f"{cfg.remote}/{cfg.branch}"
        remote_head = _git.rev_parse(self.clone, origin_ref)
        # HEAD is acceptable only AT origin/develop or strictly BEHIND it.
        on_origin = head_before == remote_head or _git.is_ancestor(
            self.clone, head_before, origin_ref
        )
        off_origin_reason = (
            f"clone HEAD {head_before[:12]} is not on {origin_ref} "
            f"({remote_head[:12]}): a local commit, or {origin_ref} was rewritten; "
            f"reset the clone by hand"
        )

        # 4. dry run: plan against origin without moving HEAD
        if cfg.dry_run:
            return self.dry_run(head_before, remote_head, on_origin, off_origin_reason)

        # 5. refuse / resume / fast-forward
        if not on_origin:
            return self.refuse(off_origin_reason, head_before)
        if head_before == remote_head:
            if self.state.applied_head == head_before:
                self.resolve_card(
                    CARD_CLONE_REFUSED, f"clone is clean again at {head_before[:12]}"
                )
                self.save()
                self.log("noop", head=head_before, detail="up to date")
                return Outcome(
                    "noop",
                    head_before=head_before,
                    head_after=head_before,
                    message="up to date",
                )
            # an earlier tick fast-forwarded here but its actions did not finish
            head_after = head_before
            self.log("resume", head=head_after, applied_head=self.state.applied_head)
        else:
            try:
                _git.merge_ff_only(self.clone, origin_ref)
            except _git.GitError as exc:
                return self.refuse(
                    f"cannot fast-forward to {origin_ref}: {exc.stderr}", head_before
                )
            head_after = _git.head(self.clone)
            self.log("fast_forward", **{"from": head_before, "to": head_after})
        self.resolve_card(
            CARD_CLONE_REFUSED, f"clone is clean again at {head_after[:12]}"
        )

        # 6. classify applied_head..HEAD
        try:
            changed = _git.changed_paths(
                self.clone, self.state.applied_head, head_after
            )
        except _git.GitError as exc:
            count = self.state.record_attempt(head_after, "diff", exc.returncode)
            self.log("classify", ok=False, count=count, detail=exc.stderr)
            if count >= cfg.max_attempts:
                return self.hold(head_before, head_after, None)
            self.save()
            return Outcome(
                "failed",
                head_before=head_before,
                head_after=head_after,
                message=f"cannot diff applied_head {self.state.applied_head}..HEAD: {exc.stderr}",
            )
        plan = classify(changed)
        self.log("classify", changed=len(changed), plan=plan.actions(), head=head_after)

        # 7. retry gate
        if self.state.failure_count(head_after) >= cfg.max_attempts:
            return self.hold(head_before, head_after, plan)

        # 8. act
        outcome = self.act(head_before, head_after, plan)
        if outcome is not None:
            return outcome

        # 9. success — attempts for this and every superseded HEAD are moot
        self.state.applied_head = head_after
        self.state.attempts.clear()
        self.resolve_card(CARD_SYNC_FAILED, f"sync succeeded at {head_after[:12]}")
        self.save()
        status = "noop" if plan.is_noop else "ok"
        ran = list(plan.actions())
        message = f"applied {head_after[:12]} ({len(changed)} paths); ran {ran or 'nothing (autoreload)'}"
        self.log(status, head=head_after, actions=ran)
        return Outcome(
            status,
            head_before=head_before,
            head_after=head_after,
            plan=plan,
            actions_run=tuple(ran),
            message=message,
        )

    def dry_run(
        self, head_before: str, remote_head: str, on_origin: bool, refusal: str
    ) -> Outcome:
        """Step 4: say what the real tick would do — including ``would REFUSE``."""
        if not on_origin:
            message = f"would REFUSE: {refusal}"
            self.log(
                "dry_run", head=head_before, remote_head=remote_head, detail=message
            )
            return Outcome(
                "dry_run",
                head_before=head_before,
                head_after=head_before,
                message=message,
            )
        base = self.state.applied_head or head_before
        plan = classify(_git.changed_paths(self.clone, base, remote_head))
        message = (
            f"would fast-forward {head_before[:12]} -> {remote_head[:12]} and run "
            f"{list(plan.actions()) or 'nothing'}"
            if head_before != remote_head
            else f"up to date at {head_before[:12]}; plan for {base[:12]}..HEAD: "
            f"{list(plan.actions()) or 'nothing'}"
        )
        self.log(
            "dry_run", plan=plan.actions(), head=head_before, remote_head=remote_head
        )
        return Outcome(
            "dry_run",
            head_before=head_before,
            head_after=head_before,
            plan=plan,
            message=message,
        )

    def act(self, head_before: str, head_after: str, plan: Plan) -> Outcome | None:
        """Step 8: run the plan; ``None`` on success, the failed Outcome otherwise.

        The attempt is on disk BEFORE the first action starts, so a tick
        killed mid-way (SIGTERM, OOM, reboot) still counts as one; every
        exception class an action can raise settles that attempt.
        """
        cfg = self.config
        ran: list[str] = []
        current = ""
        try:
            for index, action in enumerate(plan.actions()):
                current = action
                if index == 0:
                    self.state.record_attempt(head_after, action, RC_KILLED)
                else:
                    self.state.update_attempt(head_after, action, RC_KILLED)
                self.save()
                self.log("action", name=action, head=head_after, phase="start")
                if action in ("rebuild", "reload"):
                    getattr(cfg.actions, action)(self.clone)
                    cfg.actions.wait_healthy(cfg.container)
                else:
                    getattr(cfg.actions, action)(cfg.container)
                ran.append(action)
                self.log("action", name=action, head=head_after, phase="ok")
        except ActionFailed as exc:
            return self.action_failed(
                head_before=head_before,
                head_after=head_after,
                plan=plan,
                ran=ran,
                action=exc.action,
                rc=exc.rc,
                tail=exc.tail,
                message=str(exc),
            )
        except (TickInterrupted, KeyboardInterrupt) as exc:
            signum = signum_of(exc)
            return self.action_failed(
                head_before=head_before,
                head_after=head_after,
                plan=plan,
                ran=ran,
                action=current,
                rc=-signum,
                tail=f"killed by signal {signum} during {current}",
                message=f"killed by signal {signum} during {current}; attempt recorded",
                phase="killed",
            )
        except Exception as exc:
            # An action raised something other than ActionFailed (a bug, or a
            # subprocess error it did not wrap). It is still a failed attempt.
            return self.action_failed(
                head_before=head_before,
                head_after=head_after,
                plan=plan,
                ran=ran,
                action=current,
                rc=1,
                tail=repr(exc),
                message=f"{current} raised {exc!r}",
            )
        return None


# EOF
