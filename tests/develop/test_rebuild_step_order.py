"""Deploy-path step-ordering gate: irreversible work must never precede fragile work.

Regression guard for card ``hub-rebuild-cancels-slurm-before-fragile-build``.

WHAT WENT WRONG (2026-07-24, measured on the prod host)
``scripts/deploy/rebuild.sh`` cancelled **every** SLURM job as its FIRST step
(``scancel --state=RUNNING`` / ``-u root`` / ``-u scitex``) and only then ran the
image build. The build is the step most likely to fail — on that day it aborted
on the env-file interpolation bug (``hub-make-rebuild-drops-env-file``) — so a
deploy that never happened had already destroyed every user's in-flight compute.
Cancelling jobs is IRREVERSIBLE; the build is FRAGILE; ordering the irreversible
step ahead of the fragile one makes every failed attempt maximally expensive.

The cancellation exists only to stop stale job IDs surviving the container swap,
so its real constraint is "before the swap", not "before the build". Moving it
between the build and the swap preserves the intent while making a failed build
cost nothing (``set -e`` exits before any ``scancel`` runs).

WHY THIS GATE IS SHAPED THIS WAY (constitution §2, "a gate that cannot fail is
not a gate"): the predecessor gate for the sibling card asserted the *resolved
command string* — the string it asserted was correct while the deploy was broken
anyway, so it reported green for six days over a live defect. This gate instead
checks the ORDER OF OPERATIONS in the script that actually runs, and the
``test_checker_rejects_*`` cases feed it the real pre-fix arrangement to prove
the check can still go red. If those ever pass vacuously, the gate has stopped
gating.

No Docker and no secrets required, so this runs in the headless pytest matrix.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REBUILD_SH = REPO_ROOT / "scripts" / "deploy" / "rebuild.sh"

# The three ordered landmarks. Matching is deliberately behavioural — the
# invocation that DOES the thing — rather than comment text, so rewording a
# comment cannot silence the gate.
_BUILD = "build"
_CANCEL = "cancel"
_SWAP = "swap"

# The exact arrangement that shipped the 2026-07-24 incident, kept verbatim so
# the checker is always proven against a real defect rather than a strawman.
PRE_FIX_SCRIPT = "\n".join(
    [
        'echo "  1. Cleaning SLURM state..."',
        "            scancel --state=RUNNING 2>/dev/null || true",
        'echo "  2. Building Docker images..."',
        "nice -n 10 $COMPOSE_CMD build",
        "$COMPOSE_CMD up -d --remove-orphans",
    ]
)


def _is_build(line: str) -> bool:
    return "$COMPOSE_CMD build" in line and not line.lstrip().startswith("#")


def _is_cancel(line: str) -> bool:
    return "scancel" in line and not line.lstrip().startswith("#")


def _is_swap(line: str) -> bool:
    return "$COMPOSE_CMD up -d" in line and not line.lstrip().startswith("#")


def _landmark_lines(script: str) -> dict:
    """Map each landmark to the 0-based index of its FIRST occurrence.

    First occurrence is the meaningful one for ``scancel``: the earliest
    cancellation is what a failed later step would have wasted.
    """
    found: dict = {}
    for idx, line in enumerate(script.splitlines()):
        for name, pred in ((_BUILD, _is_build), (_CANCEL, _is_cancel), (_SWAP, _is_swap)):
            if name not in found and pred(line):
                found[name] = idx
    return found


def _ordering_violations(script: str) -> list:
    """Return human-readable violations of build < cancel < swap.

    A missing landmark is itself a violation: if the script is refactored such
    that a landmark no longer matches, the gate must fail loudly rather than
    silently assert nothing.
    """
    found = _landmark_lines(script)
    missing = [name for name in (_BUILD, _CANCEL, _SWAP) if name not in found]
    if missing:
        return [f"landmark {name!r} not found in script" for name in missing]

    violations = []
    if found[_CANCEL] < found[_BUILD]:
        violations.append(
            f"irreversible scancel (line {found[_CANCEL] + 1}) runs BEFORE the "
            f"fragile build (line {found[_BUILD] + 1}): a failed build destroys "
            f"users' running jobs for a deploy that never happens"
        )
    if found[_SWAP] < found[_CANCEL]:
        violations.append(
            f"container swap (line {found[_SWAP] + 1}) runs BEFORE scancel "
            f"(line {found[_CANCEL] + 1}): stale job IDs survive the swap"
        )
    return violations


def _declared_steps(script: str) -> list:
    """Return the step names from the REBUILD_STEPS header block, in order."""
    return [
        line.split("- ", 1)[0].split(". ", 1)[1].strip()
        for line in script.splitlines()
        if line.startswith("#   ") and ". " in line and "- " in line
    ]


@pytest.fixture(scope="module")
def rebuild_script() -> str:
    assert REBUILD_SH.is_file(), f"missing deploy script: {REBUILD_SH}"
    return REBUILD_SH.read_text(encoding="utf-8")


def test_live_deploy_script_orders_build_then_cancel_then_swap(rebuild_script):
    """The shipped deploy script never cancels jobs before the build can fail."""
    # Arrange
    script = rebuild_script
    # Act
    violations = _ordering_violations(script)
    # Assert
    assert violations == []


def test_declared_steps_list_build_before_slurm_clean(rebuild_script):
    """``--steps`` / ``make help-commands`` must not describe the old order.

    Both read this header block, so a stale header would misinform an operator
    mid-incident.
    """
    # Arrange
    script = rebuild_script
    # Act
    steps = _declared_steps(script)
    # Assert
    assert steps.index("build") < steps.index("slurm-clean"), steps


def test_declared_steps_include_both_landmarks(rebuild_script):
    """Guard the test above: an empty parse must not make its index check vacuous."""
    # Arrange
    script = rebuild_script
    # Act
    steps = _declared_steps(script)
    # Assert
    assert {"build", "slurm-clean"} <= set(steps), steps


def test_checker_rejects_the_historical_pre_fix_order():
    """Red-proof: the checker still fails on the arrangement that caused the incident."""
    # Arrange
    script = PRE_FIX_SCRIPT
    # Act
    violations = _ordering_violations(script)
    # Assert
    assert any("BEFORE the fragile build" in v for v in violations), violations


def test_checker_rejects_a_script_missing_a_landmark():
    """A refactor that hides a landmark must fail loudly, not pass vacuously."""
    # Arrange
    script = "echo nothing here"
    # Act
    violations = _ordering_violations(script)
    # Assert
    assert violations
