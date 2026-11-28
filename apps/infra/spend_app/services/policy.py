"""The spend-control decision table, as pure functions.

Everything that refuses or stops work asks :func:`decide` (new work) or
:func:`running_verdict` (work already running). Both are pure so the whole
behaviour matrix is tested without a database; see
``tests/apps/spend_app/test_policy.py``, which enumerates it.

New work (``decide``)::

    standing \\ action   start compute  submit job  write storage  read / delete / change cap / pay
    good, < 100 %        allow          allow       allow          allow
    good, >= 100 %       REFUSE cap     REFUSE cap  REFUSE (r/o)   allow
    past_due (grace)     allow*         allow*      allow*         allow      (* with a payment banner)
    restricted           REFUSE         REFUSE      REFUSE (r/o)   allow

Deleting is always allowed: it is how an account over its storage allowance
gets back under it, and nothing here ever deletes data on its own.

Running work (``running_verdict``): under the cap it runs; at 100 % it gets
``running_grace`` from the moment the 100 % alert fired, with a warning, then
is stopped; on a restricted account it is stopped.

Cancelling a plan (in or after the 30-day window) is not a standing: the
account falls back to the Free plan, whose catalog cap then applies.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal


class Action(enum.Enum):
    START_COMPUTE = "start_compute"
    SUBMIT_JOB = "submit_job"
    WRITE_STORAGE = "write_storage"
    READ = "read"
    DELETE_STORAGE = "delete_storage"
    CHANGE_CAP = "change_cap"
    PAY = "pay"


BILLABLE_ACTIONS = (Action.START_COMPUTE, Action.SUBMIT_JOB, Action.WRITE_STORAGE)


class Standing(enum.Enum):
    GOOD = "good"
    PAST_DUE = "past_due"
    RESTRICTED = "restricted"


class CapLevel(enum.IntEnum):
    UNDER = 0
    HALF = 50
    WARN = 80
    REACHED = 100


def cap_level(spend: Decimal, cap: Decimal) -> CapLevel:
    """Highest threshold crossed. A $0 cap is reached by any spend at all."""
    spend = Decimal(spend)
    cap = Decimal(cap)
    if cap <= 0:
        return CapLevel.REACHED if spend > 0 else CapLevel.UNDER
    ratio = spend / cap
    if ratio >= 1:
        return CapLevel.REACHED
    if ratio >= Decimal("0.8"):
        return CapLevel.WARN
    if ratio >= Decimal("0.5"):
        return CapLevel.HALF
    return CapLevel.UNDER


def percent_used(spend: Decimal, cap: Decimal) -> int:
    cap = Decimal(cap)
    if cap <= 0:
        return 100 if Decimal(spend) > 0 else 0
    return int((Decimal(spend) / cap * 100).to_integral_value())


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str = "ok"
    #: Would this have been refused in enforce mode? (True in shadow mode only.)
    shadowed: bool = False

    @property
    def refused(self) -> bool:
        return not self.allowed


ALLOW = Decision(True)


def decide(
    standing: Standing, level: CapLevel, action: Action, *, mode="enforce"
) -> Decision:
    if action not in BILLABLE_ACTIONS:
        return ALLOW
    code = None
    if standing is Standing.RESTRICTED:
        code = "account_restricted"
    elif standing is Standing.GOOD and level is CapLevel.REACHED:
        code = (
            "storage_read_only"
            if action is Action.WRITE_STORAGE
            else "spend_cap_reached"
        )
    if code is None:
        return ALLOW
    if mode == "shadow":
        return Decision(True, code, shadowed=True)
    return Decision(False, code)


class Run(enum.Enum):
    RUN = "run"
    WARN = "warn"  # still running; will be stopped at ``stop_at``
    STOP = "stop"


@dataclass(frozen=True)
class RunningVerdict:
    verdict: Run
    reason: str = ""
    stop_at: datetime | None = None


def running_verdict(
    standing: Standing,
    level: CapLevel,
    *,
    reached_at: datetime | None,
    now: datetime,
    grace: timedelta,
    mode="enforce",
) -> RunningVerdict:
    if standing is Standing.RESTRICTED:
        verdict = RunningVerdict(Run.STOP, f"account_{standing.value}")
    elif standing is Standing.GOOD and level is CapLevel.REACHED:
        start = reached_at or now
        stop_at = start + grace
        if now >= stop_at:
            verdict = RunningVerdict(Run.STOP, "spend_cap_reached", stop_at)
        else:
            verdict = RunningVerdict(Run.WARN, "spend_cap_reached", stop_at)
    else:
        return RunningVerdict(Run.RUN)
    if mode == "shadow" and verdict.verdict is Run.STOP:
        return RunningVerdict(Run.WARN, verdict.reason, verdict.stop_at)
    return verdict


def clamp_cap(requested: Decimal, *, max_cap: Decimal) -> Decimal:
    """A holder may set any cap in [0, plan maximum]; outside it is refused."""
    requested = Decimal(requested)
    if requested < 0:
        raise ValueError("The cap cannot be negative.")
    if requested > max_cap:
        raise ValueError(f"The most this plan allows is ${max_cap}.")
    return requested.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


__all__ = [
    "ALLOW",
    "Action",
    "BILLABLE_ACTIONS",
    "CapLevel",
    "Decision",
    "Run",
    "RunningVerdict",
    "Standing",
    "cap_level",
    "clamp_cap",
    "decide",
    "percent_used",
    "running_verdict",
]
