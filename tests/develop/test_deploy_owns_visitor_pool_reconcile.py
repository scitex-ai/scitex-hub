"""Deploy-path gate: the deploy must OWN the visitor-pool post-condition.

WHAT WENT WRONG (2026-08-16, measured on the prod host)
Every production deploy quarantines all 16 visitor slots. That is the boot
fail-safe in ``deployment/docker/common/scripts/entrypoint-prod.sh``
(``reconcile_visitor_slots --async``) and it is CORRECT: after a restart no
slot's on-disk state can be trusted, so nothing may be allocatable until a
worker proves it clean. Slots return only as ``celery_worker_vis`` verifies
each one.

That day they never returned. Image ``499481dded8b`` built 22:06:16 JST;
``scitex-hub-prod-django-1`` recreated 22:08:34 JST; the pool sat 16/16
quarantined for ~1h35m, during which EVERY anonymous visitor was funnelled
onto the single shared ``readonly-visitor`` account. Every signal stayed
green: containers healthy, deploy "successful", ``/api/server-health/``
"healthy". A human noticed. No signal did.

The missing piece was never the COMMAND — the entrypoint already runs it. It
was the ASSERTION. ``--async`` only DISPATCHES; every message it prints says
"dispatched", and nothing anywhere asked "did any slot actually come back?".
A deploy that declares success on dispatch rather than on outcome is exactly
constitution §2: a declaration that cannot be honoured evaporating instead of
failing. The repair meanwhile lived only inside a card comment addressed to
whoever deployed next — and the agent holding that intention died mid-deploy,
so the rule died with it (§7).

WHAT THIS GATE ASSERTS
1. The sanctioned start-up path still invokes the reconcile at all (the
   entrypoint the image actually bakes — not the decorative sibling copy).
2. The deploy script asks the OUTCOME question via the read-only
   ``visitor_pool_ready`` command, and a red answer sets ``VERIFY_FAILED``,
   i.e. it can actually fail the deploy. A check whose failure branch does
   nothing is not a gate (§2).
3. The failure hint NAMES the repair, and names the SAFE one
   (``--repair-only``). Plain ``reconcile_visitor_slots`` quarantines every
   slot including healthy ones, so recommending it against a live degraded
   pool would make things worse.
4. The gate probes with the read-only command, never with the reconcile —
   using the reconcile as a probe IS a mutation, and takes the pool down.

WHY IT IS SHAPED THIS WAY
The ``test_checker_rejects_*`` cases feed each checker the real PRE-FIX text,
so the checkers are always proven against the actual defect rather than a
strawman. If those ever pass vacuously, this gate has stopped gating.

No Docker and no secrets required, so this runs in the headless pytest matrix.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REBUILD_SH = REPO_ROOT / "scripts" / "deploy" / "rebuild.sh"
# The entrypoint the prod image actually bakes. Dockerfile.prod:
#   COPY deployment/docker/common/scripts/entrypoint-prod.sh /entrypoint.sh
# NOT deployment/docker/docker_prod/entrypoint.sh, which still exists, still
# carries its own divergent visitor-pool block, and ships nowhere.
ENTRYPOINT_SH = (
    REPO_ROOT / "deployment" / "docker" / "common" / "scripts" / "entrypoint-prod.sh"
)

RECONCILE_COMMAND = "reconcile_visitor_slots"
READY_COMMAND = "visitor_pool_ready"
SAFE_REPAIR_FLAG = "--repair-only"

# The verify block exactly as it shipped on 2026-08-16: containers, site, done.
# No question was ever asked about the visitor pool. Kept verbatim so the
# checker below is proven against the real incident.
PRE_FIX_REBUILD_VERIFY = "\n".join(
    [
        'echo -e "${CYAN}  7. Verifying the service is actually up...${NC}"',
        "VERIFY_FAILED=0",
        'STRANDED="$($COMPOSE_CMD ps -a --status=created --format \'{{.Name}}\')"',
        'if [ -n "$STRANDED" ]; then',
        "    VERIFY_FAILED=1",
        "fi",
        'if "$WAIT_HEALTHY" "$ENV" 420; then',
        '    echo "   Containers healthy"',
        "else",
        "    VERIFY_FAILED=1",
        "fi",
        'if [ "$SITE_OK" = "1" ]; then',
        '    echo "   Site answering"',
        "else",
        "    VERIFY_FAILED=1",
        "fi",
        'if [ "$VERIFY_FAILED" != "0" ]; then',
        "    exit 1",
        "fi",
    ]
)

# A gate that runs the check and then shrugs — the shape §2 names explicitly.
TOOTHLESS_GATE = "\n".join(
    [
        'echo "   Checking visitor pool readiness..."',
        'if docker exec "$DJANGO_CONTAINER" python manage.py visitor_pool_ready; then',
        '    echo "   ok"',
        "else",
        '    echo "   visitor pool not ready (continuing anyway)"',
        "fi",
    ]
)

# Using the reconcile itself as the probe. Looks like diligence; is a mutation.
# Its Phase 1 quarantines EVERY slot, healthy ones included, so this "check"
# guarantees the very outage it claims to detect.
MUTATING_PROBE_GATE = "\n".join(
    [
        'echo "   Checking visitor pool readiness..."',
        'if docker exec "$DJANGO_CONTAINER" python manage.py reconcile_visitor_slots; then',
        '    echo "   ok"',
        "else",
        "    VERIFY_FAILED=1",
        "fi",
    ]
)


def _uncommented_lines(script: str) -> list:
    """Lines that actually execute — comment text must not satisfy a gate."""
    return [
        line for line in script.splitlines() if not line.lstrip().startswith("#")
    ]


def _startup_reconcile_violations(entrypoint: str) -> list:
    """The baked start-up path must still invoke the reconcile."""
    live = _uncommented_lines(entrypoint)
    if not any(RECONCILE_COMMAND in line for line in live):
        return [
            f"the baked entrypoint no longer invokes {RECONCILE_COMMAND!r}: "
            f"nothing re-cleans the slots this deploy just quarantined, so "
            f"every anonymous visitor is served readonly-visitor forever"
        ]
    return []


def _gate_block(script: str, span: int = 20) -> list:
    """The executable lines of the visitor-pool gate, from its probe onward."""
    live = _uncommented_lines(script)
    for idx, line in enumerate(live):
        if READY_COMMAND in line or RECONCILE_COMMAND in line:
            return live[idx : idx + span]
    return []


def _deploy_gate_violations(script: str) -> list:
    """Violations of 'the deploy asserts the visitor-pool post-condition'."""
    live = _uncommented_lines(script)
    block = _gate_block(script)

    if not block:
        return [
            "the deploy script never asks whether the visitor pool has a "
            "distributable slot: it can report success while every visitor is "
            "downgraded to the shared readonly account (the 2026-08-16 outage)"
        ]

    violations = []

    if not any(READY_COMMAND in line for line in block):
        violations.append(
            f"the visitor-pool gate does not run {READY_COMMAND!r}; it probes "
            f"with {RECONCILE_COMMAND!r}, whose Phase 1 quarantines EVERY slot "
            f"including healthy ones — that is a mutation, not a probe, and it "
            f"causes the outage it claims to detect"
        )

    if not any("VERIFY_FAILED=1" in line for line in block):
        violations.append(
            "the visitor-pool gate never sets VERIFY_FAILED=1, so a red pool "
            "cannot fail the deploy: a gate that cannot fail is not a gate"
        )

    if not any('if [ "$VERIFY_FAILED" != "0" ]' in line for line in live):
        violations.append(
            "VERIFY_FAILED is never consulted, so setting it decides nothing"
        )

    return violations


def _repair_hint_violations(script: str) -> list:
    """The failure path must name the repair, and the SAFE repair."""
    block = _gate_block(script)
    if not block:
        return ["no visitor-pool gate at all, so no repair can be named"]

    hint_lines = [line for line in block if RECONCILE_COMMAND in line]
    if not hint_lines:
        return [
            "the visitor-pool failure path does not name the repair command; "
            "on 2026-08-16 the repair existed only inside a card comment "
            "addressed to whoever deployed next"
        ]
    if not any(SAFE_REPAIR_FLAG in line for line in hint_lines):
        return [
            f"the named repair omits {SAFE_REPAIR_FLAG!r}: plain "
            f"{RECONCILE_COMMAND} quarantines every slot including healthy "
            f"ones, so following this hint on a live degraded pool makes it worse"
        ]
    return []


@pytest.fixture(scope="module")
def rebuild_script() -> str:
    assert REBUILD_SH.is_file(), f"missing deploy script: {REBUILD_SH}"
    return REBUILD_SH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def entrypoint_script() -> str:
    assert ENTRYPOINT_SH.is_file(), f"missing baked entrypoint: {ENTRYPOINT_SH}"
    return ENTRYPOINT_SH.read_text(encoding="utf-8")


def test_baked_entrypoint_still_invokes_the_reconcile(entrypoint_script):
    """The sanctioned start-up path owns the reconcile — not a human runbook."""
    # Arrange
    script = entrypoint_script
    # Act
    violations = _startup_reconcile_violations(script)
    # Assert
    assert violations == []


def test_deploy_script_asserts_the_visitor_pool_post_condition(rebuild_script):
    """A deploy that leaves the pool quarantined must FAIL, not report success."""
    # Arrange
    script = rebuild_script
    # Act
    violations = _deploy_gate_violations(script)
    # Assert
    assert violations == []


def test_deploy_failure_path_names_the_safe_repair(rebuild_script):
    """The red message hands the next operator the fix, not archaeology."""
    # Arrange
    script = rebuild_script
    # Act
    violations = _repair_hint_violations(script)
    # Assert
    assert violations == []


def test_checker_rejects_the_pre_fix_verify_block():
    """Red-proof: the real 2026-08-16 verify block is still rejected."""
    # Arrange
    script = PRE_FIX_REBUILD_VERIFY
    # Act
    violations = _deploy_gate_violations(script)
    # Assert
    assert any("never asks whether the visitor pool" in v for v in violations), (
        violations
    )


def test_checker_rejects_a_gate_that_cannot_fail_the_deploy():
    """Red-proof: running the check and shrugging is not a gate."""
    # Arrange
    script = TOOTHLESS_GATE
    # Act
    violations = _deploy_gate_violations(script)
    # Assert
    assert any("cannot fail is not a gate" in v for v in violations), violations


def test_checker_rejects_probing_with_the_mutating_reconcile():
    """Red-proof: reconcile-as-probe quarantines the pool it claims to check."""
    # Arrange
    script = MUTATING_PROBE_GATE
    # Act
    violations = _deploy_gate_violations(script)
    # Assert
    assert any("mutation, not a probe" in v for v in violations), violations


def test_checker_rejects_an_entrypoint_that_dropped_the_reconcile():
    """Red-proof: deleting the start-up reconcile must fail loudly."""
    # Arrange
    script = 'echo_info "Initializing visitor pool..."\npython manage.py create_visitor_pool'
    # Act
    violations = _startup_reconcile_violations(script)
    # Assert
    assert violations


def test_checker_ignores_a_reconcile_that_is_only_a_comment():
    """Red-proof: a commented-out reconcile is not an invocation."""
    # Arrange
    script = "# python manage.py reconcile_visitor_slots --async\necho hi"
    # Act
    violations = _startup_reconcile_violations(script)
    # Assert
    assert violations
