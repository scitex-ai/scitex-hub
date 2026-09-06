#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The dev entrypoint and Django must read SCITEX_HUB_VITE_USE_BUILD alike.

Two programs decide the same thing from one environment variable, in two
languages:

  * ``config/settings/settings_dev.py`` decides whether Django reads the built
    manifest instead of pointing at the Vite dev server.
  * ``deployment/docker/docker_dev/entrypoint.sh`` decides whether to BUILD
    that manifest instead of starting the dev server.

If they disagree on a single spelling the stack lands in exactly the state this
change exists to remove: Django reads a manifest nobody built, ``get_manifest()``
returns ``{}``, every platform entry misses, and under DEBUG the first page a
visitor opens renders Django's technical 500 -- settings table included.

THIS IS NOT HYPOTHETICAL DRIFT; IT IS THE BUG THIS FILE WAS WRITTEN FOR. The
first draft of the entrypoint matched ``1|[Tt]rue|[Yy]es``, which does not match
``TRUE`` -- while ``settings_dev.py`` lowercases before comparing and does. A
stack setting ``SCITEX_HUB_VITE_USE_BUILD=TRUE`` would have had Django reading a
manifest the entrypoint never built. Caught by writing this test, not by review.

The tokens are EXTRACTED from both files rather than restated here, so the gate
fails when either side changes alone -- restating them would just add a third
copy to keep in sync.
"""

from __future__ import annotations

import ast
import re
import subprocess

import pytest

from ._compose_helpers import REPO_ROOT

SETTINGS_DEV = REPO_ROOT / "config" / "settings" / "settings_dev.py"
ENTRYPOINT = REPO_ROOT / "deployment" / "docker" / "docker_dev" / "entrypoint.sh"

VAR = "SCITEX_HUB_VITE_USE_BUILD"

# VITE_USE_BUILD = os.environ.get("SCITEX_HUB_VITE_USE_BUILD", "").lower() in (
#     "1", "true", "yes",
# )
DJANGO_TOKENS = re.compile(
    r"VITE_USE_BUILD\s*=\s*os\.environ\.get\(\s*\"" + VAR + r"\"[^)]*\)\s*"
    r"\.lower\(\)\s+in\s+(\([^)]*\))",
    re.S,
)

# The `case` line is matched loosely on purpose. The real one is
#     case "$(printf '%s' "${SCITEX_HUB_VITE_USE_BUILD:-false}" | tr ...)" in
# which carries NESTED double quotes, so a `"[^"]*"` pattern cannot span it --
# my first attempt did exactly that and matched nothing, which the harness
# control below caught. Anchor on the line carrying both `case` and the
# variable, then take the pattern list from the next non-blank line.
ENTRYPOINT_CASE = re.compile(
    r"^(\s*case\s+.*" + VAR + r".*\sin)\s*$\n(?:\s*\n)*\s*([^\n)]+)\)",
    re.M,
)


def django_truthy_tokens() -> list[str]:
    """The exact spellings settings_dev.py accepts, read from the source."""
    match = DJANGO_TOKENS.search(SETTINGS_DEV.read_text(encoding="utf-8"))
    assert match, (
        f"could not find the {VAR} tuple in {SETTINGS_DEV}. If the settings "
        "moved or were rewritten, this gate is no longer reading the thing it "
        "claims to -- fix the pattern rather than deleting the test."
    )
    return [str(t) for t in ast.literal_eval(match.group(1))]


def entrypoint_case_parts() -> tuple[str, str]:
    """(the `case ... in` line, the pattern list) from the real entrypoint."""
    match = ENTRYPOINT_CASE.search(ENTRYPOINT.read_text(encoding="utf-8"))
    assert match, (
        f"could not find a `case` on {VAR} in {ENTRYPOINT}. Either the "
        "entrypoint stopped branching on the flag -- in which case it no "
        "longer honours it -- or this pattern needs updating."
    )
    return match.group(1), match.group(2).strip()


def entrypoint_matches(value: str) -> bool:
    """Run the entrypoint's OWN case expression under bash for one value.

    The normalisation expression and the pattern list are lifted verbatim from
    entrypoint.sh, so this exercises the shipped logic rather than a
    paraphrase of it. The bodies are replaced with echoes because the real
    branch shells `npm run build` and writes to /app/logs.
    """
    case_line, patterns = entrypoint_case_parts()
    script = f"""
        {VAR}={value!r}
        {case_line}
            {patterns}) echo BUILD ;;
            *)          echo DEVSERVER ;;
        esac
    """
    result = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip() == "BUILD"


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_django_declares_a_nonempty_truthy_set():
    """If extraction silently returned nothing, every parity check below is vacuous."""
    # Arrange / Act
    tokens = django_truthy_tokens()

    # Assert
    assert tokens, "extracted an EMPTY truthy set from settings_dev.py"


def test_the_harness_can_report_devserver():
    """NEGATIVE CONTROL: a harness that always says BUILD would pass parity trivially."""
    # Arrange / Act / Assert
    assert not entrypoint_matches("false")
    assert not entrypoint_matches("")
    assert not entrypoint_matches("0")


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", django_truthy_tokens())
def test_entrypoint_builds_for_every_value_django_accepts(token):
    # Assert -- as written, and upper-cased, since Django lowercases first.
    assert entrypoint_matches(token), (
        f"settings_dev.py treats {VAR}={token!r} as ON and reads the built "
        f"manifest, but {ENTRYPOINT.name} does not build for it. Django would "
        "read a manifest nothing produced: every platform Vite entry misses "
        "and under DEBUG the first page a visitor opens renders the technical "
        "500."
    )
    assert entrypoint_matches(token.upper()), (
        f"settings_dev.py lowercases before comparing, so {VAR}="
        f"{token.upper()!r} is ON for Django -- but the entrypoint does not "
        "build for it. Same split, different spelling."
    )
