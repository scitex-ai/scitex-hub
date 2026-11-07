"""Server-resolved keymap for the hub shell runtime.

The browser shell owns dispatch, but it must not re-implement conflict or
resolution rules: every chord a user saves in Settings > Keyboard Shortcuts is
already validated there (same-scope conflicts refused, unknown IDs rejected).
This module resolves those persisted preferences into the exact matchers the
shell keydown handler compares against ``KeyboardEvent`` fields, so the
browser applies user overrides without parsing or prioritizing anything.

The matchers speak raw ``KeyboardEvent`` terms (``key``/``ctrl``/``alt``/
``shift``/``meta``), not the scitex-ui TS chord grammar (``C-``/``M-``/``S-``).
That is deliberate: hub's global chords include ``ArrowLeft``/``ArrowRight``,
which the TS grammar canonicalizes differently from what ``event.key``
reports, and the hub shell predates the registry runtime. When the shell
bundle migrates to ``scitex_ui``'s ``Keymap`` class, this module's
``registry_sequence`` field is the mechanical bridge (it is already emitted
per command); nothing in the persisted preferences needs to change.

Page-mode commands flow through untouched: any catalog entry whose
``scope`` is not ``"global"`` is resolved with the same override/unbind
semantics, and the API serves it with its scope attached. The shell activates
a mode (and resolves mode-first) once leaf apps publish their catalogs; until
then the settings UI and this endpoint already round-trip those rows.
"""

from __future__ import annotations

from typing import Any

from apps.infra.accounts_app.keymap_preferences import (
    InvalidKeymapPreference,
    build_shortcut_rows,
)

_MODIFIERS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
    "meta": "meta",
    "super": "meta",
    "win": "meta",
    "windows": "meta",
    "cmd": "meta",
    "command": "meta",
}

# Display key -> KeyboardEvent.key. Single letters are handled generically
# (case-insensitive); this table covers everything hub's catalog uses.
_NAMED_KEYS = {
    "left": "ArrowLeft",
    "arrowleft": "ArrowLeft",
    "right": "ArrowRight",
    "arrowright": "ArrowRight",
    "up": "ArrowUp",
    "arrowup": "ArrowUp",
    "down": "ArrowDown",
    "arrowdown": "ArrowDown",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "space": " ",
    " ": " ",
    "esc": "Escape",
    "escape": "Escape",
    "delete": "Delete",
    "del": "Delete",
    "backspace": "Backspace",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
}

# Display modifier -> scitex-ui TS chord-grammar token (C/M/S/M2). Kept as the
# mechanical bridge for the future registry migration; the shell does not read it.
_REGISTRY_MODIFIERS = {"ctrl": "C", "alt": "M", "shift": "S", "meta": "M2"}

# KeyboardEvent.key -> TS grammar key for the bridge field.
_REGISTRY_NAMED_KEYS = {
    "ArrowLeft": "LFT",
    "ArrowRight": "RGT",
    "ArrowUp": "UP",
    "ArrowDown": "DWN",
    "Enter": "RET",
    " ": "SPAC",
    "Escape": "ESC",
    "Delete": "DEL",
    "PageUp": "PGUP",
    "PageDown": "PGDN",
    "Home": "BEG",
    "End": "END",
}


def parse_display_matcher(sequence: str) -> dict[str, Any]:
    """Parse one display sequence (``"Alt+Shift+Left"``) into event fields.

    Hub's catalog is single-chord; multi-chord input (whitespace-separated,
    e.g. ``"C-x C-s"``) is rejected so a registry-style string can never slip
    into the shell matcher path untranslated.
    """
    candidate = " ".join(str(sequence).split())
    if not candidate:
        raise InvalidKeymapPreference("Shortcut sequence must contain 1-128 characters")
    parts = [part.strip() for part in candidate.split("+")]
    if any(not part for part in parts) or any(" " in part for part in parts):
        # Interior whitespace means a second chord ("C-x C-s"); the hub shell
        # is single-chord and registry-style strings must never slip through
        # untranslated.
        if any(" " in part for part in parts):
            raise InvalidKeymapPreference(
                f"Multi-chord sequences are not supported by the hub shell: {sequence!r}"
            )
        raise InvalidKeymapPreference(f"Invalid shortcut sequence: {sequence!r}")
    *modifiers, raw_key = parts
    flags = {"ctrl": False, "alt": False, "shift": False, "meta": False}
    for modifier in modifiers:
        flag = _MODIFIERS.get(modifier.casefold())
        if flag is None:
            raise InvalidKeymapPreference(f"Unknown modifier: {modifier!r}")
        flags[flag] = True
    key: str
    if len(raw_key) == 1:
        key = raw_key.casefold()
    else:
        resolved = _NAMED_KEYS.get(raw_key.casefold())
        if resolved is None and not (
            raw_key.casefold().startswith("f")
            and raw_key[1:].isdigit()
            and 1 <= int(raw_key[1:]) <= 12
        ):
            raise InvalidKeymapPreference(f"Unknown key: {raw_key!r}")
        key = resolved if resolved is not None else f"F{int(raw_key[1:])}"
    return {"key": key, **flags}


def to_registry_sequence(sequence: str) -> str:
    """Translate one display sequence into scitex-ui TS chord grammar.

    ``"Alt+Shift+Left"`` -> ``"M-S-LFT"``. Bridge field for the future
    registry migration; the current shell matcher path does not read it.
    """
    matcher = parse_display_matcher(sequence)
    tokens: list[str] = [
        _REGISTRY_MODIFIERS[flag]
        for flag in ("ctrl", "alt", "shift", "meta")
        if matcher[flag]
    ]
    raw_key = matcher["key"]
    if len(raw_key) == 1:
        grammar_key = raw_key.upper()
    else:
        grammar_key = _REGISTRY_NAMED_KEYS.get(raw_key, raw_key)
    tokens.append(grammar_key)
    return "-".join(tokens)


def effective_keymap(
    preferences: dict[str, Any] | None,
    defaults: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve defaults + persisted prefs into shell matchers, keyed by command.

    Each entry carries the display ``sequence`` (``None`` when unbound), the
    ``match`` struct the shell compares against ``KeyboardEvent`` fields
    (``None`` when unbound), the ``registry_sequence`` bridge string, and the
    row metadata (scope/label/group/default). Unbound commands are present
    with ``bound: False`` so the shell can disable their default chord.
    """
    if defaults is None:
        from scitex_ui.keymap import keymap_defaults  # type: ignore[import-not-found]

        defaults = keymap_defaults()
    assert defaults is not None
    commands: dict[str, dict[str, Any]] = {}
    for row in build_shortcut_rows(defaults, preferences):
        command_id = row["command_id"]
        sequence: str | None = row["effective_sequence"] or None
        if row["is_unbound"]:
            sequence = None
        commands[command_id] = {
            "scope": row["scope"],
            "label": row["label"],
            "group": row["group"],
            "default_sequence": row["default_sequence"],
            "sequence": sequence,
            "match": parse_display_matcher(sequence) if sequence else None,
            "registry_sequence": to_registry_sequence(sequence) if sequence else None,
            "bound": sequence is not None,
            "is_overridden": row["is_overridden"],
            "is_unbound": row["is_unbound"],
        }
    return commands


__all__ = ["effective_keymap", "parse_display_matcher", "to_registry_sequence"]
