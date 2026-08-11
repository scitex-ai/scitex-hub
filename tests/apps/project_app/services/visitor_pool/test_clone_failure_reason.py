#!/usr/bin/env python3
"""A failed template clone must say WHY, in the string the operator reads.

Card scitex-clone-template-bare-bool-destroys-the-failure-reason-20260811.

THE INCIDENT THIS LOCKS. On 2026-08-06 the visitor pool quarantined 14 of 16
slots. The entire operator-visible explanation, written verbatim into
``VisitorAllocation.quarantine_reason`` (slot_lifecycle.py:101), was:

    "reset failed: Template clone returned falsy for default-project"

No cause, no file, no next step. Nobody could act on it, so nobody did, and
every anonymous visitor was funnelled onto one shared account for five days.

The reason existed. ``clone_scitex_minimal`` caught the exception and logged the
traceback — to the LOGGER. The consumer three frames up read the RETURN VALUE,
and ``bool`` has nowhere to put a sentence. scitex-template 0.7.0 added
``clone_template_result() -> CloneOutcome`` to carry it; these tests assert the
hub actually surfaces it rather than re-flattening it on arrival.

WHY A HAND-ROLLED STAND-IN AND NOT THE REAL CloneOutcome: scitex_template is not
installed in every environment these tests run in, and importing it would make
the suite skip exactly where it matters. The stand-in mirrors the published
shape (ok / status / template_id / project_dir / reason) and, crucially, these
tests assert on the CONSUMER's behaviour — what string reaches the operator —
which is hub's responsibility and is testable without the package. The real
contract is locked upstream in scitex-template's own suite.

No mocks of the code under test. One assertion per test (STX-TQ007).
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from apps.infra.project_app.services.visitor_pool.template_clone import (
    clone_template_into,
    describe_clone_failure,
)

# The message the incident produced. Nothing we emit may look like this again.
VACUOUS_MESSAGE_FRAGMENT = "returned falsy"


@dataclass(frozen=True)
class FakeOutcome:
    """Mirrors scitex_template.CloneOutcome's published shape."""

    ok: bool
    status: str
    template_id: str
    project_dir: str
    reason: Optional[str] = None

    def __bool__(self) -> bool:
        return self.ok


def _failed(reason: Optional[str]) -> FakeOutcome:
    return FakeOutcome(
        ok=False,
        status="failed",
        template_id="scitex_minimal",
        project_dir="/data/users/visitor-001/proj/default-project",
        reason=reason,
    )


def test_the_reason_reaches_the_message():
    """THE POINT OF THE CARD. The template's own words must survive."""
    # Arrange
    outcome = _failed("scitex_writer.ensure_workspace raised PermissionError")
    # Act
    message = describe_clone_failure(outcome)
    # Assert
    assert "PermissionError" in message


def test_the_message_names_the_template_and_directory():
    """Half of any actionable message is WHERE. Both are in the outcome."""
    # Arrange
    outcome = _failed("boom")
    # Act
    message = describe_clone_failure(outcome)
    # Assert
    assert "scitex_minimal" in message and "default-project" in message


def test_a_missing_reason_is_reported_as_missing_not_as_silence():
    """`reason=None` is THREE-VALUED: "did not say", never "fine".

    Collapsing unknown into either pole is the bug this whole card is about.
    A template that fails without a reason is itself the actionable finding —
    it names a clone function still discarding its own cause — so the message
    must say so rather than emitting an empty or generic string.
    """
    # Arrange
    outcome = _failed(None)
    # Act
    message = describe_clone_failure(outcome)
    # Assert
    assert "NO reason" in message


def test_a_bare_bool_is_named_as_the_caller_s_fault_not_the_template_s():
    """A legacy injected clone_fn must not look like a silent template.

    If this said "the template reported no reason" it would send the reader to
    scitex-template to debug a callable that was never asked for a reason.
    """
    # Arrange
    outcome = False
    # Act
    message = describe_clone_failure(outcome)
    # Assert
    assert "bare bool" in message


def test_no_failure_message_is_the_vacuous_one():
    """THE REGRESSION GUARD. None of the shapes may read like the incident."""
    # Arrange
    shapes = [_failed("boom"), _failed(None), False, object()]
    # Act
    messages = [describe_clone_failure(s) for s in shapes]
    # Assert
    assert not [m for m in messages if VACUOUS_MESSAGE_FRAGMENT in m]


FAILURE_REASON = "scitex_scholar.ensure_workspace bound a module, not a callable"


def _raise_from_failed_clone() -> str:
    """Run a failing clone and return the raised message."""
    clone_fn = lambda *a, **k: _failed(FAILURE_REASON)  # noqa: E731
    try:
        clone_template_into("/tmp/x", "scitex_minimal", clone_fn)
    except RuntimeError as exc:
        return str(exc)
    return ""


def test_clone_template_into_raises_on_failure():
    """A failed clone must not return quietly — the slot has to quarantine."""
    # Arrange
    clone_fn = lambda *a, **k: _failed(FAILURE_REASON)  # noqa: E731
    # Act / assert below is the raises block itself
    # Assert
    with pytest.raises(RuntimeError):
        clone_template_into("/tmp/x", "scitex_minimal", clone_fn)


def test_the_raised_message_carries_the_reason():
    """That raise becomes quarantine_reason verbatim, so it carries the cause."""
    # Arrange
    expected = FAILURE_REASON
    # Act
    message = _raise_from_failed_clone()
    # Assert
    assert expected in message


def test_clone_template_into_returns_the_outcome_on_success():
    """POSITIVE CONTROL: the success path is not accidentally raising.

    Without this, every assertion above would still pass if
    `clone_template_into` raised unconditionally.
    """
    # Arrange
    ok = FakeOutcome(ok=True, status="cloned", template_id="scitex_minimal",
                     project_dir="/tmp/x")
    clone_fn = lambda *a, **k: ok  # noqa: E731
    # Act
    result = clone_template_into("/tmp/x", "scitex_minimal", clone_fn)
    # Assert
    assert result is ok


# EOF
