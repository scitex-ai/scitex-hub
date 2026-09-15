#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every `-c` setting Django puts in `options` must be tracked by pgbouncer.

WHY THIS TEST EXISTS — it is a post-incident gate, not a precaution.

2026-09-06: `options` was removed from `ignore_startup_parameters` so pgbouncer
would APPLY `-c` settings instead of silently discarding them, and
`track_extra_parameters = search_path` was added alongside. That change was
tested carefully — three arms, per-client tracking verified under transaction
pooling, refusal verified by name.

Every arm exercised `search_path`. **Nothing in hub sends search_path.** What
hub sends is `settings_prod.py: "options": "-c statement_timeout=30000"`, and
`statement_timeout` was not in the tracked list. One second after the config
reached production:

    pooler error: unsupported startup parameter in options: statement_timeout

365 rejected connections, /auth/login/ 500 for ~5 minutes, every container
healthcheck green throughout (pg_isready proves the port accepts; the refusal
happens later, at startup-parameter negotiation).

The controls were sound. The POPULATION was wrong — the rule was verified
against a parameter no client uses. This test fixes the population to the one
that matters: what the settings actually send.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ._compose_helpers import REPO_ROOT

INI = REPO_ROOT / "deployment" / "docker" / "common" / "pgbouncer" / "pgbouncer.ini"
SETTINGS_DIR = REPO_ROOT / "config" / "settings"

# "options": "-c statement_timeout=30000"   (any number of -c pairs)
OPTIONS_VALUE = re.compile(r'"options"\s*:\s*"([^"]*-c[^"]*)"')
DASH_C_PARAM = re.compile(r"-c\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def sent_parameters() -> dict[str, str]:
    """{parameter: 'file:line'} for every -c setting the settings send."""
    found: dict[str, str] = {}
    for path in sorted(SETTINGS_DIR.glob("*.py")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for value in OPTIONS_VALUE.findall(line):
                for param in DASH_C_PARAM.findall(value):
                    found.setdefault(param, f"{path.name}:{n}")
    return found


def tracked_parameters() -> set[str]:
    """The parameters pgbouncer will accept inside `options`."""
    for line in INI.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(";") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() == "track_extra_parameters":
            return {p.strip() for p in value.split(",") if p.strip()}
    return set()


def ignores_options_wholesale() -> bool:
    """True if `options` is back in ignore_startup_parameters (the old defect)."""
    for line in INI.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(";") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() == "ignore_startup_parameters":
            return "options" in {p.strip() for p in value.split(",")}
    return False


# ---------------------------------------------------------------------------
# Controls — a sweep that finds nothing would pass the rule vacuously
# ---------------------------------------------------------------------------


def test_the_ini_exists_and_declares_tracking():
    assert INI.is_file(), f"{INI} is missing; this gate is not reading anything"
    assert tracked_parameters(), (
        "track_extra_parameters is absent or empty. Either pgbouncer tracks "
        "nothing (and every -c setting is refused), or the parser broke — and "
        "a parser that returns an empty set makes the rule below vacuous."
    )


def test_the_scan_finds_the_options_django_actually_sends():
    """If this returns nothing, the rule cannot fail and proves nothing."""
    sent = sent_parameters()
    assert sent, (
        "no `\"options\": \"-c ...\"` found anywhere in config/settings/. That is "
        "the exact population this gate exists to compare against, so an empty "
        "result means the scan broke, not that nothing is sent."
    )


def test_the_detector_would_notice_an_untracked_parameter():
    """POSITIVE CONTROL for the comparison itself."""
    assert "zzz_not_a_real_guc" not in tracked_parameters()


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("param,origin", sorted(sent_parameters().items()))
def test_every_option_sent_is_tracked(param, origin):
    if ignores_options_wholesale():
        pytest.skip(
            "`options` is in ignore_startup_parameters, so pgbouncer discards "
            "the whole thing and refuses nothing. That is the ORIGINAL defect "
            "(silent discard) rather than this one, and it has its own card."
        )

    assert param in tracked_parameters(), (
        f"{origin} sends `-c {param}=...` inside `options`, and pgbouncer's "
        f"track_extra_parameters is {sorted(tracked_parameters())}. Any -c "
        "setting not named there is REFUSED at connection setup with "
        f"'unsupported startup parameter in options: {param}' — every new "
        "pooled connection fails and the container healthcheck stays green, "
        "because pg_isready only proves the port accepts. This exact mismatch "
        "took production down on 2026-09-06. Add it to track_extra_parameters "
        "and RESTART (not SIGHUP) the pooler."
    )
