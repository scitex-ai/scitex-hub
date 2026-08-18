#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/_click_compat.py

"""Guarded access to scitex-dev's shared CLI-standardization helpers.

The shared helpers — ``deprecated_alias`` (the W->E->R deprecation
ladder, scitex-dev#307) and ``CliHelp``/``SpecCommand``/``SpecGroup``
(spec-built categorized help, scitex-dev#308) — live on scitex-dev
``develop`` but have NOT shipped in a release yet (the latest tag,
v0.28.0, predates both). Following the scitex-python#352 pattern:

* with a new-enough scitex-dev the deprecated aliases and the
  spec-built categorized help ACTIVATE;
* with a released scitex-dev the canonical command names still work,
  the warn-phase aliases are simply not registered (Click's
  unknown-command error applies), and docstring help renders instead
  of spec-built help.

Once scitex-dev releases with the helpers, bump the ``scitex-dev``
floor in pyproject.toml and collapse the fallbacks here.
"""

from __future__ import annotations

import click

try:  # scitex-dev develop (> v0.28.0) — helpers not yet in a release
    from scitex_dev.ecosystem import (
        CliHelp,
        Example,
        SpecCommand,
        SpecGroup,
        deprecated_alias,
    )

    HAS_CLI_HELPERS = True
except ImportError:  # released scitex-dev — skip-with-comment (see module doc)
    CliHelp = Example = SpecCommand = SpecGroup = deprecated_alias = None
    HAS_CLI_HELPERS = False

__all__ = [
    "HAS_CLI_HELPERS",
    "register_error_redirect",
    "register_warn_alias",
    "spec_command_kwargs",
    "spec_group_kwargs",
]


def spec_command_kwargs(*, summary, examples, description=()):
    """Decorator kwargs for a spec-built leaf (doctrine §4), or ``{}``.

    ``examples`` is a sequence of ``(cmd, note)`` pairs; commands use
    the ``{prog}`` placeholder. With a released scitex-dev this returns
    ``{}`` so the plain ``click.Command`` + docstring help applies.
    """
    if not HAS_CLI_HELPERS:
        return {}
    return {
        "cls": SpecCommand,
        "help_spec": CliHelp(
            summary=summary,
            description=description,
            examples=tuple(Example(cmd, note) for cmd, note in examples),
        ),
    }


def spec_group_kwargs(
    *,
    summary,
    examples=(),
    description=(),
    version_of=None,
    command_categories=None,
):
    """Decorator kwargs for a spec-built group (doctrine §4/§4a), or ``{}``.

    ``command_categories`` follows the canonical seven-category order
    (Core / Data & Sync / Service / Diagnostics / Introspection /
    Shell; ``Other`` is the auto catch-all and must stay empty).
    """
    if not HAS_CLI_HELPERS:
        return {}
    kwargs = {
        "cls": SpecGroup,
        "help_spec": CliHelp(
            summary=summary,
            description=description,
            examples=tuple(Example(cmd, note) for cmd, note in examples),
            version_of=version_of,
        ),
    }
    if command_categories is not None:
        kwargs["command_categories"] = command_categories
    return kwargs


def register_warn_alias(group, old_name, *, target, remove_in, target_name=None):
    """Register a warn-phase deprecated alias (ladder §W), if possible.

    With a released scitex-dev the shared ladder helper is unavailable
    and the old spelling is simply NOT registered (skip-with-comment,
    scitex-python#352 precedent) — no duplicate local ladder
    implementation is shipped.
    """
    if not HAS_CLI_HELPERS:
        return None
    return deprecated_alias(
        group,
        old_name,
        target=target,
        remove_in=remove_in,
        phase="warn",
        target_name=target_name,
    )


def register_error_redirect(group, old_name, *, target, remove_in):
    """Register an error-phase redirect (exit 2), with a local fallback.

    Unlike the warn aliases, these spellings were ALREADY erroring
    before this slice, so the behavior is preserved on a released
    scitex-dev via a local redirect instead of being skipped.
    """
    if HAS_CLI_HELPERS:
        return deprecated_alias(
            group, old_name, target=target, remove_in=remove_in, phase="error"
        )

    @click.pass_context
    def _impl(ctx, **_):
        click.echo(
            f"error: `scitex-hub {old_name}` was renamed to "
            f"`scitex-hub {target}`.\n"
            f"Re-run with: scitex-hub {target} [...]",
            err=True,
        )
        ctx.exit(2)

    cmd = click.command(
        old_name,
        hidden=True,
        context_settings={
            "ignore_unknown_options": True,
            "allow_extra_args": True,
        },
    )(_impl)
    group.add_command(cmd)
    return cmd


# EOF
