# -*- coding: utf-8 -*-
# File: tests/config/_compose_helpers.py
"""Shared compose-file reading for the ``tests/config`` interface gates.

Underscore-prefixed so pytest does not collect it as a test module.

WHY THIS EXISTS. Two gates now ask the same question of every compose file --
"does this ``ports:`` entry reach beyond loopback?" -- for two different
populations: ``test_compose_keeps_debug_stacks_off_public_interfaces.py`` asks it
of stacks whose ``DEBUG`` defaults to True, and
``test_compose_keeps_datastores_off_public_interfaces.py`` asks it of databases
and caches. A second copy of the parser is not merely untidy: the two copies
would answer differently the day one of them learns about a compose form the
other has not, and the gate that stayed behind would keep reporting clean. One
parser, one answer.

The parser is deliberately the only thing shared. Each gate keeps its own
population rule, its own controls, and its own failure message, because those are
the parts that must stay legible to whoever the gate stops.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Discovered, not enumerated, so a compose file added tomorrow is covered without
# anyone remembering to list it. The count control in each gate keeps discovery
# honest: a glob that silently matches nothing reports "clean" because it never ran.
COMPOSE_GLOB = "deployment/**/*compose*.y*ml"

# Measured 2026-08-04: 10 compose files under deployment/. The floor sits below
# that deliberately -- it is a tripwire for "discovery broke", not a headcount to
# be edited whenever a file is legitimately added or retired.
MIN_EXPECTED_COMPOSE_FILES = 8

# Addresses that keep a port off the network. "::1" is here because a v6-only
# loopback bind is equally safe and refusing it would be a false positive.
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")

# What a gate is handed for a compose file it could not parse. A malformed file is
# another test's problem, but it must not silently drop out of a sweep and read as
# clean, so it is injected as a service that FAILS every interface rule.
UNPARSEABLE_SERVICE = "<unparseable>"
UNPARSEABLE_PORTS = ["0.0.0.0:1:1"]


def compose_files():
    """Every compose file under ``deployment/``, sorted for stable test ids."""
    return sorted(REPO_ROOT.glob(COMPOSE_GLOB))


def environment(service):
    """Compose accepts both ``KEY: value`` and ``- KEY=value``. Normalise."""
    env = service.get("environment")
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items() if v is not None}
    if isinstance(env, list):
        out = {}
        for item in env:
            key, sep, value = str(item).partition("=")
            if sep:
                out[key.strip()] = value.strip()
        return out
    return {}


def published_on_public_interface(entry):
    """True when this ``ports:`` entry reaches beyond loopback.

    Handles compose's short form (``"127.0.0.1:8000:8000"``, ``"8000:8000"``,
    ``"8000"``) and its long form (a mapping with ``host_ip``).
    """
    if isinstance(entry, dict):
        # Long form. No `published` means the port is not published at all.
        if entry.get("published") in (None, ""):
            return False
        return str(entry.get("host_ip") or "").strip() not in LOOPBACK_HOSTS
    text = str(entry).strip().strip('"').strip("'")
    if not text:
        return False
    # A leading interface is present only when the entry has three colon-parts
    # AND the first is not a ${...} port variable. Match the known loopback
    # spellings from the left so that "${VAR:-8000}:8000" -- whose default syntax
    # contains a colon -- is not mistaken for an interface.
    for host in LOOPBACK_HOSTS:
        if text.startswith(host + ":"):
            return False
    return True


def services(path):
    """``(service_name, service_dict)`` for one compose file.

    A file that will not parse yields a single synthetic service publishing on
    every interface, so the caller's sweep goes RED rather than quietly shrinking.
    """
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return [(UNPARSEABLE_SERVICE, {"ports": list(UNPARSEABLE_PORTS)})]
    if not isinstance(doc, dict):
        return []
    return [
        (name, svc)
        for name, svc in (doc.get("services") or {}).items()
        if isinstance(svc, dict)
    ]
