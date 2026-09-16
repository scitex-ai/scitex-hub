"""Pure helpers for persisted per-user keymap overrides.

The browser runtime owns chord parsing and dispatch. Hub owns durable user
preferences, conflict refusal, and reset semantics. Keeping this module free of
Django imports makes the contract cheap to test and safe to reuse from views,
APIs, and agents.
"""

from __future__ import annotations

import copy
import re
from typing import Any

_VERSION = 1
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_PLUS_SPACING_RE = re.compile(r"\s*\+\s*")
_WHITESPACE_RE = re.compile(r"\s+")


class KeymapConflictError(ValueError):
    """A sequence is already assigned to another command in the same scope."""


class InvalidKeymapPreference(ValueError):
    """A persisted scope, command ID, or sequence is not safe to store."""


def empty_preferences() -> dict[str, Any]:
    """Return the canonical empty preference document."""
    return {"version": _VERSION, "bindings": {}, "unbound": {}}


def _identifier(value: str, label: str) -> str:
    candidate = str(value).strip()
    if not _IDENTIFIER_RE.fullmatch(candidate):
        raise InvalidKeymapPreference(f"Invalid {label}: {value!r}")
    return candidate


def _sequence(value: str) -> str:
    candidate = _WHITESPACE_RE.sub(" ", str(value).strip())
    candidate = _PLUS_SPACING_RE.sub("+", candidate)
    if not candidate or len(candidate) > 128:
        raise InvalidKeymapPreference("Shortcut sequence must contain 1-128 characters")
    return candidate


def _document(preferences: dict[str, Any] | None) -> dict[str, Any]:
    if preferences is None:
        return empty_preferences()
    document = copy.deepcopy(preferences)
    document.setdefault("version", _VERSION)
    document.setdefault("bindings", {})
    document.setdefault("unbound", {})
    if document["version"] != _VERSION:
        raise InvalidKeymapPreference(
            f"Unsupported keymap preference version: {document['version']!r}"
        )
    if not isinstance(document["bindings"], dict) or not isinstance(
        document["unbound"], dict
    ):
        raise InvalidKeymapPreference("Bindings and unbound preferences must be objects")
    return document


def _drop_empty_scope(document: dict[str, Any], section: str, scope: str) -> None:
    if not document[section].get(scope):
        document[section].pop(scope, None)


def _validate_catalog_command(
    catalog: dict[str, dict[str, Any]] | None, scope: str, command_id: str
) -> None:
    if catalog is None:
        return
    command = catalog.get(command_id)
    if command is None:
        raise InvalidKeymapPreference(f"Unknown command ID: {command_id}")
    expected_scope = str(command.get("scope") or "global")
    if scope != expected_scope:
        raise InvalidKeymapPreference(
            f"Command {command_id} belongs to {expected_scope}, not {scope}"
        )


def _refuse_effective_catalog_conflict(
    document: dict[str, Any],
    catalog: dict[str, dict[str, Any]] | None,
    scope: str,
    command_id: str,
    sequence: str,
) -> None:
    if catalog is None:
        return
    scoped_bindings = document["bindings"].get(scope, {})
    disabled = document["unbound"].get(scope, [])
    target = sequence.casefold()
    for other_id, other_command in catalog.items():
        other_scope = str(other_command.get("scope") or "global")
        if other_scope != scope or other_id == command_id or other_id in disabled:
            continue
        effective = scoped_bindings.get(other_id, other_command.get("sequence") or "")
        if effective and _sequence(effective).casefold() == target:
            raise KeymapConflictError(
                f"{sequence} is already assigned to {other_id} in {scope}"
            )


def bind_shortcut(
    preferences: dict[str, Any] | None,
    scope: str,
    command_id: str,
    sequence: str,
    *,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return preferences with one override, refusing same-scope conflicts."""
    document = _document(preferences)
    scope = _identifier(scope, "scope")
    command_id = _identifier(command_id, "command ID")
    sequence = _sequence(sequence)
    _validate_catalog_command(catalog, scope, command_id)
    _refuse_effective_catalog_conflict(document, catalog, scope, command_id, sequence)
    conflict_key = sequence.casefold()

    scoped_bindings = document["bindings"].setdefault(scope, {})
    if not isinstance(scoped_bindings, dict):
        raise InvalidKeymapPreference(f"Bindings for scope {scope!r} must be an object")
    for existing_command_id, existing_sequence in scoped_bindings.items():
        if existing_command_id == command_id:
            continue
        if _sequence(existing_sequence).casefold() == conflict_key:
            raise KeymapConflictError(
                f"{sequence} is already assigned to {existing_command_id} in {scope}"
            )

    scoped_bindings[command_id] = sequence
    disabled = document["unbound"].get(scope, [])
    if not isinstance(disabled, list):
        raise InvalidKeymapPreference(f"Unbound commands for scope {scope!r} must be a list")
    document["unbound"][scope] = [item for item in disabled if item != command_id]
    _drop_empty_scope(document, "unbound", scope)
    return document


def unbind_shortcut(
    preferences: dict[str, Any] | None,
    scope: str,
    command_id: str,
    *,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return preferences that explicitly disable one default/overridden command."""
    document = _document(preferences)
    scope = _identifier(scope, "scope")
    command_id = _identifier(command_id, "command ID")
    _validate_catalog_command(catalog, scope, command_id)

    scoped_bindings = document["bindings"].get(scope, {})
    if not isinstance(scoped_bindings, dict):
        raise InvalidKeymapPreference(f"Bindings for scope {scope!r} must be an object")
    scoped_bindings.pop(command_id, None)
    _drop_empty_scope(document, "bindings", scope)

    disabled = document["unbound"].setdefault(scope, [])
    if not isinstance(disabled, list):
        raise InvalidKeymapPreference(f"Unbound commands for scope {scope!r} must be a list")
    if command_id not in disabled:
        disabled.append(command_id)
        disabled.sort()
    return document


def reset_shortcuts(
    preferences: dict[str, Any] | None,
    *,
    scope: str | None = None,
    command_id: str | None = None,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reset one command to its default, or reset every override when omitted."""
    if scope is None and command_id is None:
        return empty_preferences()
    if scope is None or command_id is None:
        raise InvalidKeymapPreference("scope and command_id must be provided together")

    document = _document(preferences)
    scope = _identifier(scope, "scope")
    command_id = _identifier(command_id, "command ID")
    _validate_catalog_command(catalog, scope, command_id)

    scoped_bindings = document["bindings"].get(scope, {})
    if not isinstance(scoped_bindings, dict):
        raise InvalidKeymapPreference(f"Bindings for scope {scope!r} must be an object")
    scoped_bindings.pop(command_id, None)
    _drop_empty_scope(document, "bindings", scope)

    disabled = document["unbound"].get(scope, [])
    if not isinstance(disabled, list):
        raise InvalidKeymapPreference(f"Unbound commands for scope {scope!r} must be a list")
    document["unbound"][scope] = [item for item in disabled if item != command_id]
    _drop_empty_scope(document, "unbound", scope)
    return document


def build_shortcut_rows(
    defaults: dict[str, dict[str, Any]],
    preferences: dict[str, Any] | None,
    *,
    query: str = "",
) -> list[dict[str, Any]]:
    """Build searchable settings rows with default and effective sequences."""
    document = _document(preferences)
    needle = query.strip().casefold()
    rows: list[dict[str, Any]] = []
    for command_id, command in defaults.items():
        scope = _identifier(str(command.get("scope") or "global"), "scope")
        label = str(command.get("label") or command_id)
        group = str(command.get("group") or scope)
        default_sequence = str(command.get("sequence") or "")
        scoped_bindings = document["bindings"].get(scope, {})
        if not isinstance(scoped_bindings, dict):
            raise InvalidKeymapPreference(
                f"Bindings for scope {scope!r} must be an object"
            )
        disabled = document["unbound"].get(scope, [])
        if not isinstance(disabled, list):
            raise InvalidKeymapPreference(
                f"Unbound commands for scope {scope!r} must be a list"
            )
        is_unbound = command_id in disabled
        is_overridden = command_id in scoped_bindings
        effective_sequence = (
            ""
            if is_unbound
            else scoped_bindings.get(command_id, default_sequence)
        )
        haystack = " ".join((command_id, label, group, scope)).casefold()
        if needle and needle not in haystack:
            continue
        rows.append(
            {
                "command_id": command_id,
                "label": label,
                "group": group,
                "scope": scope,
                "default_sequence": default_sequence,
                "effective_sequence": effective_sequence,
                "is_overridden": is_overridden,
                "is_unbound": is_unbound,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["group"].casefold(),
            row["label"].casefold(),
            row["command_id"],
        ),
    )


__all__ = [
    "InvalidKeymapPreference",
    "KeymapConflictError",
    "bind_shortcut",
    "build_shortcut_rows",
    "empty_preferences",
    "reset_shortcuts",
    "unbind_shortcut",
]
