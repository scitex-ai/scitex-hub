#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared decorators / helpers for §2 universal-flag conformance.

The SciTeX CLI noun-verb convention (§2, universal-flags.md) requires:

* Read verbs (list/show/get/...) expose ``--json`` for machine consumption.
* Mutating verbs (create/delete/install/...) expose ``--dry-run`` to print the
  planned action and ``--yes/-y`` to skip the interactive confirmation prompt.

These decorators add the flags in a uniform way so individual command files
don't drift on naming or default values. The decorators are purely additive —
they never alter the wrapped function's signature beyond appending the
keyword-only ``json_output``, ``dry_run``, ``yes`` parameters that Click
already injects.

No silent fallback: every helper either does the thing or surfaces a real
error. Confirmation is flag-driven only (§2: never prompt): a mutating verb
without ``--yes/-y`` refuses with exit code 2 so every invocation is
deterministic, interactive or not.
"""

from __future__ import annotations

import json as _json
from typing import Any, Callable

import click

# Names that Click will assign on the wrapped function. Centralised so tests
# and consumers can import the constants instead of re-typing literals.
JSON_PARAM = "json_output"
DRY_RUN_PARAM = "dry_run"
YES_PARAM = "yes"


def json_flag() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator adding ``--json/--no-json`` to a read verb.

    The flag is exposed in Click as ``json_output`` (rather than ``json``) to
    avoid shadowing the stdlib :mod:`json` import inside command bodies.
    """

    return click.option(
        "--json/--no-json",
        "json_output",
        default=False,
        help="Output as JSON for machine consumption.",
    )


def dry_run_flag() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator adding ``--dry-run/--no-dry-run`` to a mutating verb."""

    return click.option(
        "--dry-run/--no-dry-run",
        default=False,
        help="Show what would happen without executing.",
    )


def yes_flag() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator adding ``-y/--yes/--no-yes`` to a mutating verb."""

    return click.option(
        "-y",
        "--yes/--no-yes",
        default=False,
        help="Confirm the action (required for mutating verbs; never prompts).",
    )


def mutating_flags() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator stacking ``--dry-run`` + ``--yes`` on a mutating verb."""

    def _wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        return dry_run_flag()(yes_flag()(func))

    return _wrap


def emit_json(payload: Any) -> None:
    """Serialise *payload* with :func:`json.dumps` and print to stdout.

    Uses ``default=str`` so common but non-JSON-native types (``Path``,
    ``datetime``, etc.) round-trip without callers writing custom encoders.
    """

    click.echo(_json.dumps(payload, indent=2, sort_keys=True, default=str))


def confirm_or_abort(message: str, *, yes: bool, dry_run: bool = False) -> bool:
    """Return True iff the caller is cleared to perform the mutation.

    Semantics (§2 — never prompt):
      * If ``dry_run`` — return ``False`` (caller should print the plan and
        exit cleanly).
      * If ``yes`` — return ``True`` immediately.
      * Otherwise refuse: print an error explaining that confirmation is
        flag-driven and exit ``2``. There is no interactive prompt — the
        same invocation behaves identically on a TTY and in a pipeline.
    """

    if dry_run:
        return False
    if yes:
        return True
    click.echo(
        f"error: confirmation required: {message}\n"
        "This command never prompts — re-run with --yes/-y to proceed, "
        "or --dry-run to preview.",
        err=True,
    )
    raise SystemExit(2)


def print_dry_run(action: str) -> None:
    """Print a uniform ``[dry-run] ...`` plan line.

    Centralised so the format is consistent across verbs and the test suite
    can assert against a single substring.
    """

    click.echo(f"[dry-run] {action}")


# EOF
