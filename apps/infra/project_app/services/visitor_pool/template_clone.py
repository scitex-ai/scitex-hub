"""Step 6 of the visitor reset: clone the template and verify its marker.

Extracted from ``workspace_manager.py``, which documents itself as a 7-step
orchestrator whose other steps already live in their own modules
(``container_teardown``, ``workspace_wipe``, ``home_state``). The clone step was
the one that never got one.

WHY THIS MODULE CARES SO MUCH ABOUT THE FAILURE MESSAGE. Whatever
:func:`clone_template_into` raises is caught by the caller and written verbatim
into ``VisitorAllocation.quarantine_reason`` (slot_lifecycle.py:101), which is
the ENTIRE operator-visible account of why a visitor slot is dead. On 2026-08-06
that account read, for five days, across 14 of 16 slots:

    "reset failed: Template clone returned falsy for default-project"

No cause, no file, no next step. The reason existed at the failure site inside
scitex-template and was discarded one frame later by a ``-> bool`` return.
scitex-template 0.7.0 added ``clone_template_result() -> CloneOutcome`` to carry
it; this module is the consumer that makes it reach a human.
"""

import logging
from pathlib import Path

from ..writer_workspace_layout import WRITER_WORKSPACE_RELPATH

logger = logging.getLogger(__name__)

# The template marker IS the Writer workspace directory, so it is not spelled
# here — it is imported from the one module that owns that path (2026-07-08
# incident: this was ``scitex/writer`` — no dot — while the REAL
# ``scitex_template.clone_scitex_minimal`` / ``scitex_writer.ensure_workspace``
# create dot-prefixed ``.scitex/writer`` + ``.scitex/scholar``, so verification
# never passed and every slot was quarantined; then 2026-08-02, writer_app was
# found still carrying the undotted spelling in 8 places).
# Verified against scitex-writer 2.17.5 and 2.26.1.
# tests/apps/project_app/services/visitor_pool/test_template_marker_reality.py
# locks the VALUE against the real packages and guards every consumer.
TEMPLATE_MARKER_RELPATH = WRITER_WORKSPACE_RELPATH


def verify_template_marker(project_path: Path) -> bool:
    """True if the cloned template's marker content is present.

    Marker = ``.scitex/writer/`` (:data:`TEMPLATE_MARKER_RELPATH`) exists and is
    non-empty (the same check the pool initializer uses for readiness).
    """
    writer_dir = Path(project_path) / TEMPLATE_MARKER_RELPATH
    try:
        return writer_dir.is_dir() and any(writer_dir.iterdir())
    except OSError:
        return False


def describe_clone_failure(outcome) -> str:
    """Render a FAILED clone as something an operator can act on.

    Three shapes are handled EXPLICITLY rather than falling through to one
    generic string, because "I could not tell why" and "the template said why"
    must not read the same:

    * ``CloneOutcome`` (scitex-template >= 0.7.0) — report its ``reason``; when
      ``reason`` is None say THAT, because None means "this template did not
      say" and is itself the actionable fact — it names a clone function whose
      failure path still swallows its own cause.
    * a bare ``bool`` — only reachable when a caller injects a legacy
      ``clone_fn``. Named explicitly, so the message never implies the template
      declined to explain when in truth nobody asked it to.
    * anything else — report the repr and type. A contract violation is worth
      seeing, not hiding behind prose.
    """
    if isinstance(outcome, bool):
        return (
            "the injected clone callable returned a bare bool, which cannot "
            "carry a reason — pass scitex.template.clone_template_result "
            "(scitex-template>=0.7.0) to get one"
        )
    status = getattr(outcome, "status", None)
    if status is None:
        return f"clone callable returned {outcome!r} (type {type(outcome).__name__})"
    reason = getattr(outcome, "reason", None)
    template_id = getattr(outcome, "template_id", "?")
    if reason:
        return (
            f"{reason} [status={status}, template={template_id}, "
            f"dir={getattr(outcome, 'project_dir', '?')}]"
        )
    return (
        f"status={status} but the template reported NO reason — the clone "
        f"function for template {template_id!r} is still discarding its cause"
    )


def resolve_clone_callable():
    """The clone entry point that can explain itself.

    ``clone_template`` returns a bare bool and is deliberately NOT used here.
    Raises ImportError with the pin to move if the installed scitex-template is
    too old, rather than silently degrading to the bool API — a silent
    downgrade here would restore the exact blindness this module exists to end.
    """
    from scitex.template import clone_template_result

    return clone_template_result


def clone_template_into(project_path: Path, template_id: str, clone_fn=None):
    """Clone ``template_id`` into ``project_path``; return the outcome.

    Raises
    ------
    RuntimeError
        On any failure, with a message naming the cause. The caller wraps this
        in ``WorkspaceResetError`` so the slot is quarantined with a reason a
        human can act on.
    """
    if clone_fn is None:
        clone_fn = resolve_clone_callable()

    outcome = clone_fn(template_id, str(project_path), git_strategy=None)

    if not outcome:
        raise RuntimeError(describe_clone_failure(outcome))

    return outcome


# EOF
