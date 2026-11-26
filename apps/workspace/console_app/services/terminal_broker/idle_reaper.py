"""Idle auto-stop and spend-cap stop for interactive terminals.

Runs inside the terminal broker, the only process that owns the PTYs and the
SLURM allocations behind them. Every ``CHECK_INTERVAL`` seconds, per user:

1. IDLE. With no keystroke in and no byte out on any of the user's shells for
   ``SPEND_CONTROLS["idle_stop_minutes"]`` (default 30), the allocation is
   stopped, after a warning ``idle_warning_minutes`` (default 5) before. A
   process that is still printing counts as busy, so a running computation is
   not mistaken for an idle prompt. Idle terminals therefore stop billing
   instead of billing silently (pricing decision #2).
2. SPEND. ``spend_app.services.enforcement.terminal_verdict``: at 100 % of the
   cap the user is warned and the session keeps running through the grace
   window; when it ends (or the account is restricted) the allocation stops.
3. BOOKKEEPING. An open terminal ``WorkloadSession`` with no live allocation or
   session left (expired, crashed, broker restarted) is closed, so its
   allocation clock stops.

Both stops write a line into every attached terminal before closing it.
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .broker import TerminalBroker

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30  # seconds
SPEND_CHECK_INTERVAL = 60  # seconds between DB verdicts per user


def _settings():
    from django.conf import settings

    return settings.SPEND_CONTROLS


class IdleReaper:
    def __init__(self, broker: "TerminalBroker", *, clock=time.time, verdict_fn=None):
        self.broker = broker
        self._clock = clock
        self._verdict_fn = verdict_fn
        self._stop = threading.Event()
        self._thread = None
        self._idle_warned: set[str] = set()
        self._spend_warned: set[str] = set()
        self._last_spend_check: dict[str, float] = {}

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="idle-reaper"
        )
        self._thread.start()
        logger.info("IdleReaper started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        from django.db import close_old_connections

        while not self._stop.is_set():
            try:
                close_old_connections()
                self.check_once()
            except Exception:
                logger.exception("IdleReaper check failed")
            self._stop.wait(CHECK_INTERVAL)

    # -- helpers -------------------------------------------------------------

    def _ptys_by_user(self) -> dict[str, list]:
        with self.broker.lock:
            ptys = list(self.broker.shells.values()) + list(
                self.broker.sessions.values()
            )
        by_user: dict[str, list] = {}
        for pty in ptys:
            by_user.setdefault(pty.username, []).append(pty)
        return by_user

    def _say(self, ptys, text: str) -> None:
        payload = base64.b64encode(f"\r\n\x1b[1;33m{text}\x1b[0m\r\n".encode()).decode(
            "ascii"
        )
        for pty in ptys:
            sock = getattr(pty, "client_socket", None)
            if sock is None:
                continue
            try:
                self.broker._send_message(
                    sock,
                    {"action": "output", "session_id": pty.pty_id, "data": payload},
                )
            except Exception:
                pass

    def _stop_user(self, username: str, ptys, *, reason: str) -> None:
        """Stop every interactive PTY/allocation of ``username``."""
        from apps.infra.spend_app.services.workloads import close_workloads_for_username

        from ._handlers_shared import handle_stop_allocation

        # Record the REAL reason first: handle_stop_allocation closes any
        # still-open record as a user stop.
        close_workloads_for_username(username, kind="terminal", reason=reason)
        with self.broker.lock:
            has_alloc = (username,) in self.broker.alloc_index
        if has_alloc:
            handle_stop_allocation(self.broker, {"username": username})
        for pty in ptys:  # legacy per-tab sessions (and any shell left over)
            with self.broker.lock:
                self.broker.sessions.pop(pty.pty_id, None)
                self.broker.shells.pop(pty.pty_id, None)
                self.broker.session_index = {
                    k: v
                    for k, v in self.broker.session_index.items()
                    if v != pty.pty_id
                }
                self.broker.shell_index = {
                    k: v for k, v in self.broker.shell_index.items() if v != pty.pty_id
                }
            try:
                pty.close()
            except Exception:
                pass
        self._idle_warned.discard(username)
        self._spend_warned.discard(username)
        logger.info("IdleReaper: stopped interactive session(s) of a user (%s)", reason)

    def _verdict(self, username):
        if self._verdict_fn is not None:
            return self._verdict_fn(username)
        from apps.infra.spend_app.services.enforcement import terminal_verdict

        return terminal_verdict(username)

    # -- the check -----------------------------------------------------------

    def check_once(self) -> None:
        from apps.infra.spend_app.services.policy import Run

        cfg = _settings()
        idle_limit = cfg["idle_stop_minutes"] * 60
        warn_at = max(0, idle_limit - cfg["idle_warning_minutes"] * 60)
        now = self._clock()

        live = self._ptys_by_user()
        for username, ptys in live.items():
            idle = now - max(p.last_activity for p in ptys)
            if idle_limit > 0 and idle >= idle_limit:
                self._say(
                    ptys,
                    f"Session stopped after {cfg['idle_stop_minutes']} minutes without "
                    "activity, so it stops billing. Your files are saved; open the "
                    "terminal again to start a new session.",
                )
                self._stop_user(username, ptys, reason="idle")
                continue
            if idle_limit > 0 and idle >= warn_at and username not in self._idle_warned:
                self._idle_warned.add(username)
                remaining = int((idle_limit - idle) // 60) or 1
                self._say(
                    ptys,
                    f"No activity for a while: this session stops in about {remaining} "
                    "minute(s) unless you type something.",
                )
            elif idle < warn_at:
                self._idle_warned.discard(username)

            if now - self._last_spend_check.get(username, 0) < SPEND_CHECK_INTERVAL:
                continue
            self._last_spend_check[username] = now
            verdict = self._verdict(username)
            if verdict.verdict is Run.STOP:
                self._say(
                    ptys,
                    "Session stopped: "
                    + (
                        "your account is restricted after a failed payment."
                        if verdict.reason.startswith("account_")
                        else "your monthly spend cap was reached and the grace period ended."
                    )
                    + " Nothing was deleted.",
                )
                self._stop_user(
                    username,
                    ptys,
                    reason="restricted"
                    if verdict.reason.startswith("account_")
                    else "spend_cap",
                )
            elif verdict.verdict is Run.WARN and username not in self._spend_warned:
                self._spend_warned.add(username)
                when = (
                    verdict.stop_at.strftime("%H:%M UTC") if verdict.stop_at else "soon"
                )
                self._say(
                    ptys,
                    f"Monthly spend cap reached: this session will be stopped at {when}. "
                    "Save your work. Raise your cap in Settings > Spend controls.",
                )

        self._close_orphans(set(live))

    def _close_orphans(self, live_users: set) -> None:
        from apps.infra.spend_app.models import WorkloadSession

        with self.broker.lock:
            alloc_users = {key[0] for key in self.broker.alloc_index}
        alive = live_users | alloc_users
        for row in WorkloadSession.objects.filter(
            kind=WorkloadSession.Kind.TERMINAL, stopped_at__isnull=True
        ).select_related("user"):
            if row.user.username not in alive:
                from django.utils import timezone

                row.stopped_at = timezone.now()
                row.stop_reason = WorkloadSession.StopReason.LOST
                row.save(update_fields=["stopped_at", "stop_reason"])


__all__ = ["IdleReaper"]
