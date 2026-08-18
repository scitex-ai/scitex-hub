#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No compose `command:` / `entrypoint:` may carry a secret.

WHY THIS TEST EXISTS. A secret passed as a command-line argument is readable by
any user on the host: it sits in ``/proc/<pid>/cmdline`` and a bare ``ps aux``
prints it in full. On 2026-08-03 the Cloudflare tunnel token did exactly that --
it was written into an agent's session transcript by a routine ``ps aux`` run to
answer an unrelated question, and a transcript is append-only, so the disclosure
cannot be taken back.

THE PART THAT MAKES THIS A GATE RATHER THAN A ROTATION. Rotating the token does
not fix it. The exposure RATE is a property of the STORAGE LOCATION, so a fresh
token in argv is disclosed again by the next ``ps``. The only fix is to move the
secret off the command line -- which is a one-line config change that anybody
can undo in a one-line config change, months later, while "just adding a flag".
That is precisely the kind of rule that is forgotten at the moment it matters,
so it is encoded here instead of in a comment.

WHY THE SWEEP COVERS DORMANT FILES TOO, unlike its sibling
``test_compose_entrypoints_keep_tini.py`` which deliberately gates only the
files that launch running containers. The reasoning genuinely differs and the
difference is worth stating, because otherwise one of the two looks wrong:
  - tini: gating a dead file would fail CI over a container nobody runs, which
    teaches people to edit the test to go green. Restricting to live files is
    what keeps that gate honest.
  - secrets: the dormant file is the COPY SOURCE. ``docker-compose.prod.yml``
    launches nothing today and still carried the identical ``--token`` line,
    because it was copied from -- or to -- the live one. A template that teaches
    the wrong pattern is the mechanism by which this returns.
Both files were fixed in the same change, so this sweep is green over all of
them; it is not aspirational.

WHY ``tests/config/`` -- see the sibling's docstring. PS-302 masks a FIXED list
of legacy top-level ``tests/`` subdirectories, so adding a new one is itself an
audit violation and trips the ratchet. Compose files are configuration.

WHY "credentials" AND NOT "secrets" IN THE FILENAME -- do not rename it back.
This file was written as ``test_compose_keeps_secrets_out_of_argv.py`` and
``.gitignore:37`` is ``**/*secret*``, so git silently refused to track it. It ran
green locally, it would have been committed with no error, and it would simply
never have existed in CI. That is the failure mode this whole file exists to
prevent, one level up: a gate that is not on the path that executes is
indistinguishable from a gate that passes. Any future test about credential
handling hits the same rule -- ``git check-ignore -v <path>`` before assuming a
new test file is committed.
"""

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Discovered rather than enumerated, so a compose file added tomorrow is covered
# without anyone remembering to list it here. The count control below is what
# keeps discovery honest -- a glob that silently matches nothing is the classic
# way a sweep reports "clean" because it never ran.
_COMPOSE_GLOB = "deployment/**/*compose*.y*ml"

# Measured 2026-08-03: ``git ls-tree -r origin/develop`` lists 10 compose files
# under deployment/. The floor is deliberately below that -- it is a tripwire for
# "discovery broke", not a headcount that must be edited whenever a file is
# legitimately added or retired.
_MIN_EXPECTED_COMPOSE_FILES = 8

# Flags whose VALUE is a credential. Matched on the flag token itself, so
# ``--token``, ``--token=x`` and ``--token x`` are all caught.
_SECRET_FLAGS = (
    "--token",
    "--password",
    "--passwd",
    "--api-key",
    "--apikey",
    "--secret",
    "--auth-token",
    "--access-key",
)

# Interpolations whose NAME says the value is a credential. This is the second
# half of the net: a flag can be renamed, but ``${...TOKEN}`` on a command line
# is a secret in argv whatever the flag is called.
_SECRET_VAR_MARKERS = ("TOKEN", "PASSWORD", "PASSWD", "SECRET", "API_KEY", "APIKEY")


def _tokens(value):
    """Normalise compose's string-or-list form to a flat list of tokens."""
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    return [str(part) for part in value]


def _offences(tokens):
    """Every reason this argv would leak a secret. Empty list == clean."""
    found = []
    for token in tokens:
        bare = token.split("=", 1)[0]
        if bare in _SECRET_FLAGS:
            found.append(f"secret-bearing flag {bare!r}")
        if "${" in token or token.startswith("$"):
            upper = token.upper()
            for marker in _SECRET_VAR_MARKERS:
                if marker in upper:
                    found.append(f"interpolated secret variable in {token!r}")
                    break
    return found


def _compose_files():
    return sorted(_REPO_ROOT.glob(_COMPOSE_GLOB))


def _cases():
    """(path, service, key, tokens) for every command/entrypoint in every file."""
    out = []
    for path in _compose_files():
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            # A malformed compose file is a different test's problem, but it must
            # not silently drop out of THIS sweep and read as clean.
            out.append((path, "<unparseable>", "<none>", ["--token", "PARSE-FAILED"]))
            continue
        if not isinstance(doc, dict):
            continue
        for name, svc in (doc.get("services") or {}).items():
            if not isinstance(svc, dict):
                continue
            for key in ("command", "entrypoint"):
                tokens = _tokens(svc.get(key))
                if tokens:
                    out.append((path, name, key, tokens))
    return out


_ALL = _cases()


def test_compose_discovery_found_the_expected_files():
    # Arrange -- THE DISCOVERY CONTROL. Without it, a directory rename turns the
    # glob into zero files and every assertion below passes by finding nothing,
    # which is indistinguishable from finding nothing wrong.
    files = _compose_files()
    # Act
    count = len(files)
    # Assert
    assert count >= _MIN_EXPECTED_COMPOSE_FILES, (
        f"compose discovery found only {count} file(s) under {_COMPOSE_GLOB!r} "
        f"(expected at least {_MIN_EXPECTED_COMPOSE_FILES}). The sweep below is "
        f"vacuous until this is fixed -- do not lower the floor to go green."
    )


def test_sweep_actually_found_command_definitions():
    # Arrange -- THE POPULATION CONTROL, one level down: files can be found while
    # every command/entrypoint key is missed (a schema change, a key rename).
    cases = _ALL
    # Act
    count = len(cases)
    # Assert
    assert count > 0


def test_detector_flags_a_known_violation():
    # Arrange -- THE POSITIVE CONTROL, and the one that matters most here. Every
    # other assertion in this file is a NEGATIVE one ("no secret is present"),
    # and a negative assertion passes for free when the detector is broken. This
    # is the exact line this change removed from docker_prod/docker-compose.yml.
    leaky = "tunnel --no-autoupdate run --token ${SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN_PROD}"
    # Act
    offences = _offences(_tokens(leaky))
    # Assert
    assert offences, (
        "the detector failed to flag a line that is KNOWN to leak a secret in "
        "argv, so every 'clean' verdict in this file is meaningless"
    )


def test_detector_accepts_the_fixed_form():
    # Arrange -- the NEGATIVE control that pairs with the positive one above. A
    # detector that flags everything would also make the sweep useless, in the
    # opposite direction: it would be edited away rather than obeyed.
    fixed = "tunnel --no-autoupdate run"
    # Act
    offences = _offences(_tokens(fixed))
    # Assert
    assert offences == []


@pytest.mark.parametrize(
    "path,service,key,tokens",
    _ALL,
    ids=[f"{p.name}::{s}::{k}" for p, s, k, _ in _ALL],
)
def test_no_secret_on_the_command_line(path, service, key, tokens):
    # Arrange
    rel = path.relative_to(_REPO_ROOT)
    # Act
    offences = _offences(tokens)
    # Assert
    assert offences == [], (
        f"{rel} service '{service}' passes a secret via {key}: "
        f"{'; '.join(offences)}. Anything in argv is world-readable through "
        f"/proc and printed by `ps aux`, so rotating the value does not help -- "
        f"the next `ps` discloses the new one. Move it to the environment:\n"
        f"    {key}: <the command WITHOUT the secret flag>\n"
        f"    environment:\n"
        f"      TUNNEL_TOKEN: ${{YOUR_VAR}}\n"
        f"Most images accept their credential from an env var for this reason."
    )
