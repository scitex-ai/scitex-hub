#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_logging_merge.py
"""Compose an environment's logging config ONTO the base, instead of over it.

WHY THIS MODULE EXISTS
----------------------
Every environment module starts with ``from .settings_shared import *``, which
binds the base ``LOGGING`` dict, and then used to refine it with::

    LOGGING.update({"handlers": {...}, "loggers": {...}})

``dict.update`` REPLACES a top-level key outright. So that call kept whatever
the environment's ``loggers`` literal happened to list and silently threw away
every logger the base had wired. Measured on 2026-08-15 against the real
modules: ``settings_prod`` reduced the base's eleven loggers to four and left
``mail_admins`` -- the operator notification rail -- defined as a handler and
referenced by nothing. ``settings_staging`` did the same. The wiring survived
only in ``settings_dev``, which happened to spread ``**LOGGING.get("loggers")``
-- and dev is the one environment where ``require_debug_false`` blocks the mail
anyway. Net admin emails delivered: zero, while the config read as if it worked.

Spreading ``**LOGGING.get("loggers", {})`` in each environment would fix that
day and leave the same trap for the next edit. This module removes the trap:
``merge_logging`` is the ONE supported way to refine the base, it merges by
name instead of replacing sections, and it REFUSES a result that has lost the
operator rail or that defines a handler no logger uses. A mistake of this shape
now fails loudly at import with the reason, instead of passing every review and
delivering nothing.

It also returns a NEW dict rather than mutating the base. ``LOGGING`` is the
same object in ``settings_logging``, ``settings_shared`` and every environment
module (star-import binds, it does not copy), so the old in-place ``update``
also meant that importing two environment modules in one process left the
second one reading the first one's edits. Tests that compose environments -- the
gate in ``tests/config/test_admin_error_mail.py`` -- depend on that no longer
being true.
"""

from __future__ import annotations

from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured

# Sections of a dictConfig that map NAME -> definition. These are merged entry
# by entry, so an environment redefining one entry keeps all the others. Every
# other top-level key ("version", "disable_existing_loggers", "root") is a
# single value, and an environment that sets it means to replace it.
_SECTIONS_KEYED_BY_NAME = ("formatters", "filters", "handlers", "loggers")

# The handler that carries a failure out of the machine and to a person.
OPERATOR_RAIL_HANDLER = "mail_admins"

# A handler may legitimately be referenced by no logger ONLY when something
# attaches it by name at runtime. Each entry needs a written reason; this is
# deliberately not a wildcard, because a blanket exemption would hide every
# future instance of the defect this module exists to prevent.
HANDLERS_WITH_NO_LOGGER_BY_DESIGN = frozenset(
    {
        # A no-op sink attached on demand to silence a third-party logger.
        "null",
    }
)


def merge_logging(base: dict, override: dict) -> dict:
    """Return ``base`` refined by ``override``, with nothing silently dropped.

    ``handlers``, ``loggers``, ``filters`` and ``formatters`` are merged BY
    NAME: an entry present in ``override`` replaces that one entry, and every
    entry the environment did not mention survives. Any other key is replaced.

    Raises ``ImproperlyConfigured`` -- at import, naming the problem -- when the
    merged result would define a handler no logger references, or when the
    environment has detached the operator rail from a logger the base attached
    it to. Both are silent-in-production failures otherwise.
    """
    merged = deepcopy(base)
    for key, value in override.items():
        if key in _SECTIONS_KEYED_BY_NAME:
            section = merged.setdefault(key, {})
            if not isinstance(section, dict) or not isinstance(value, dict):
                raise ImproperlyConfigured(
                    f"LOGGING[{key!r}] must be a mapping of name -> definition "
                    f"in both the base and the override; got {type(section).__name__} "
                    f"and {type(value).__name__}."
                )
            section.update(deepcopy(value))
        else:
            merged[key] = deepcopy(value)

    problems = check_logging_wiring(merged, base)
    if problems:
        raise ImproperlyConfigured(
            "This environment's LOGGING override loses wiring the base set up:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
        )
    return merged


def handlers_referenced_by_loggers(config: dict) -> set[str]:
    """Every handler name some logger (or the root logger) actually uses."""
    referenced: set[str] = set()
    for logger in config.get("loggers", {}).values():
        referenced.update(logger.get("handlers", []))
    referenced.update(config.get("root", {}).get("handlers", []))
    return referenced


def loggers_carrying_the_operator_rail(config: dict) -> set[str]:
    """Logger names this config routes to the operator notification rail."""
    return {
        name
        for name, logger in config.get("loggers", {}).items()
        if OPERATOR_RAIL_HANDLER in logger.get("handlers", [])
    }


def check_logging_wiring(config: dict, base: dict) -> list[str]:
    """Describe every way ``config`` has lost wiring ``base`` established.

    Returned as a list of sentences rather than raised, so the same check can
    be run over a composed environment from a test without importing the
    settings module twice.
    """
    problems: list[str] = []

    orphaned = (
        set(config.get("handlers", {}))
        - handlers_referenced_by_loggers(config)
        - HANDLERS_WITH_NO_LOGGER_BY_DESIGN
    )
    if orphaned:
        problems.append(
            f"handlers defined but referenced by no logger: {sorted(orphaned)}. "
            "A configured-but-unattached handler reads as a working safety "
            "mechanism to anyone who greps for it while doing nothing at all. "
            "Attach it to the loggers it serves, delete it, or -- if it is "
            "attached by name at runtime -- list it in "
            "HANDLERS_WITH_NO_LOGGER_BY_DESIGN with the reason."
        )

    detached = loggers_carrying_the_operator_rail(
        base
    ) - loggers_carrying_the_operator_rail(config)
    if detached:
        problems.append(
            f"loggers that lost {OPERATOR_RAIL_HANDLER!r}: {sorted(detached)}. "
            "The base attaches the operator rail to these because they carry "
            "operational failure; redefining one here without re-listing "
            f"{OPERATOR_RAIL_HANDLER!r} sends its errors to a rotating log file "
            "and nobody else. This is how the visitor pool sat 14/16 "
            "quarantined for four days in August 2026."
        )

    return problems


# EOF
