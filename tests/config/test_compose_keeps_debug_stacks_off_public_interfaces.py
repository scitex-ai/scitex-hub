#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A stack whose ``DEBUG`` defaults to True may only publish on loopback.

WHY THIS TEST EXISTS. On 2026-08-04 ``scitex-hub-dev-django-1`` was found
listening on ``0.0.0.0:31295`` with ``DEBUG=True``, measured on the running
container rather than inferred::

    ports  8000/tcp -> HostIp 0.0.0.0, HostPort 31295
    env    SCITEX_HUB_DJANGO_DEBUG=True   DEBUG=True

With ``DEBUG=True`` an unhandled 500 returns Django's technical error page to
whoever asked: the full settings dict, the SQL that ran, local variables at
every frame, and the process environment. No login is involved. Django's own
redaction is name-matching heuristics over setting KEYS, so anything whose name
does not look like a secret is printed in full.

WHY IT IS A GUARD AND NOT A NOTE. The fix is one interface prefix, and the
regression is *also* one interface prefix -- deleted months later by someone
adding a port, who has no reason to know the rule. That is exactly the class of
rule that is forgotten at the moment it matters. The repo already proves the
point: ``docker-compose.preview.yml`` gets this right AND explains why in a
comment, and the two files gated here still got it wrong. A comment on one file
does not constrain its siblings.

WHAT THE RULE IS NOT. It is not "never bind 0.0.0.0". ``docker-compose.staging.yml``
publishes ``0.0.0.0:31294`` deliberately -- staging is public through the
Cloudflare tunnel, and ``settings_staging.py`` defaults ``DEBUG`` to False. Prod
is the same. Gating on the bind address alone would fail those two legitimately,
and a gate that fails correct code gets edited away. So the rule pairs the two
facts: DEBUG-defaults-True AND published off-loopback.

WHY "DEFAULTS TO True" RATHER THAN "IS True". We cannot read the deployed
environment from a test, and the env var is what actually decides. Defaulting to
True means the UNSET case -- a fresh checkout, a forgotten ``.env``, a CI runner
-- is the dangerous one. Gating the default is gating the case nobody chose.

THE LIMIT OF THIS GUARD, stated because a partial gate presented as a total one
is worse than none. The container that prompted this test runs from
``/home/ywatanabe/scitex-hub-dev-preview/docker-compose.yml``, which is NOT in
this repository. This test cannot see that file and fixing the files below does
not fix that container. Repo hygiene and the live host are two separate jobs;
this is only the first.

WHY ``tests/config/`` -- compose files are configuration, and PS-302 masks a
FIXED list of legacy top-level ``tests/`` subdirectories, so inventing a new one
would itself trip the audit ratchet. Same reasoning as the sibling
``test_compose_keeps_credentials_out_of_argv.py``, whose control structure this
file deliberately mirrors.

AND CHECK ``git check-ignore -v`` ON ANY NEW TEST FILE. The sibling was first
written as ``...keeps_secrets...`` and ``.gitignore`` carries ``**/*secret*``,
so git silently refused to track it -- it would have run green locally and never
existed in CI. A gate that is not on the path that executes is indistinguishable
from a gate that passes.
"""

import re

import pytest

# The compose parser lives in a shared helper so this gate and its datastore
# sibling (test_compose_keeps_datastores_off_public_interfaces.py) can never
# disagree about what "published beyond loopback" means. Two copies would answer
# differently the day one learns a compose form the other has not, and the gate
# left behind would keep reporting clean. Each gate still owns its own
# population rule, controls and failure message.
from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    UNPARSEABLE_PORTS,
    UNPARSEABLE_SERVICE,
    compose_files,
    environment,
    published_on_public_interface,
    services,
)

_REPO_ROOT = REPO_ROOT
_MIN_EXPECTED_COMPOSE_FILES = MIN_EXPECTED_COMPOSE_FILES

_SETTINGS_DIR = _REPO_ROOT / "config" / "settings"

# Both spellings appear in this repo; ADR-0001 keeps the unprefixed name as a
# legacy alias, and several services set only one of the two.
_SETTINGS_KEYS = ("DJANGO_SETTINGS_MODULE", "SCITEX_HUB_DJANGO_SETTINGS_MODULE")

# `DEBUG = os.getenv("NAME", "True")` -- the default is group 1. A module with no
# DEBUG assignment at all (settings_shared.py) yields None, which is treated as
# "not debug-defaulting" by _defaults_debug_true and asserted below.
_DEBUG_DEFAULT_RE = re.compile(
    r"^\s*DEBUG\s*=\s*os\.getenv\(\s*[\"'][^\"']+[\"']\s*,\s*[\"']([^\"']*)[\"']",
    re.MULTILINE,
)


def _defaults_debug_true(settings_module):
    """True when this settings module leaves DEBUG on with the env var unset.

    ``settings_module`` is a dotted path such as
    ``config.settings.settings_dev``. An unreadable or absent module returns
    True, not False: a settings module we cannot parse must not quietly buy a
    service an exemption from the rule.
    """
    if not settings_module:
        return False
    path = _SETTINGS_DIR / (settings_module.rsplit(".", 1)[-1] + ".py")
    if not path.is_file():
        return True
    match = _DEBUG_DEFAULT_RE.search(path.read_text(encoding="utf-8"))
    if match is None:
        return False
    return match.group(1).strip().lower() in ("true", "1", "yes")


def _settings_module(service):
    env = environment(service)
    for key in _SETTINGS_KEYS:
        if env.get(key):
            return env[key]
    return None


# Kept as module-local names so this file's own control tests still read as
# assertions about the parser THIS gate uses.
_published_on_public_interface = published_on_public_interface
_compose_files = compose_files


def _cases():
    """(path, service, settings_module, ports) for every DEBUG-defaulting service."""
    out = []
    for path in _compose_files():
        for name, svc in services(path):
            if name == UNPARSEABLE_SERVICE:
                # A malformed compose file is another test's problem, but it must
                # not silently drop out of THIS sweep and read as clean.
                out.append(
                    (path, name, "config.settings.settings_dev", list(UNPARSEABLE_PORTS))
                )
                continue
            module = _settings_module(svc)
            if not module or not _defaults_debug_true(module):
                continue
            ports = svc.get("ports") or []
            if ports:
                out.append((path, name, module, list(ports)))
    return out


_ALL = _cases()


def test_compose_discovery_found_the_expected_files():
    # Arrange -- THE DISCOVERY CONTROL. Without it a directory rename turns the
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


def test_sweep_actually_found_debug_defaulting_services():
    # Arrange -- THE POPULATION CONTROL. Files can be discovered while every
    # service is skipped: an environment-key rename, a settings-module move, or
    # a regex that stops matching all produce an empty sweep that reports clean.
    cases = _ALL
    # Act
    count = len(cases)
    # Assert
    assert count > 0, (
        "no DEBUG-defaulting service with published ports was found in any "
        "compose file. Either the environment keys changed, or "
        "_defaults_debug_true stopped recognising the settings modules. Until "
        "this finds something, the rule below is enforced against nothing."
    )


def test_debug_detector_recognises_the_dev_settings():
    # Arrange -- POSITIVE CONTROL for the crux function. Every real assertion in
    # this file is negative ("nothing is exposed"), and a negative assertion
    # passes for free when the detector silently answers False for everything.
    # settings_dev.py:63 defaults SCITEX_HUB_DJANGO_DEBUG to "True".
    module = "config.settings.settings_dev"
    # Act
    detected = _defaults_debug_true(module)
    # Assert
    assert detected, (
        "the DEBUG detector failed to recognise settings_dev, which is KNOWN to "
        "default DEBUG=True, so every 'clean' verdict in this file is meaningless"
    )


@pytest.mark.parametrize("module", ["config.settings.settings_prod", "config.settings.settings_staging"])
def test_debug_detector_clears_the_non_debug_settings(module):
    # Arrange -- NEGATIVE CONTROL. A detector that answered True for everything
    # would fail staging and prod, whose public binds are correct and deliberate.
    # That gate would be deleted rather than obeyed, so it must be shown not to
    # over-trigger, not merely to trigger.
    # Act
    detected = _defaults_debug_true(module)
    # Assert
    assert not detected, (
        f"{module} defaults DEBUG to False but the detector flagged it. This "
        f"guard would fail a correct public bind, which is how a gate gets "
        f"removed instead of followed."
    )


def test_port_parser_flags_a_bind_on_all_interfaces():
    # Arrange -- POSITIVE CONTROL for the parser. This is the exact string from
    # deployment/docker/docker_dev/docker-compose.yml:104 that this change fixes.
    entry = "${SCITEX_HUB_HTTP_PORT_DEV:-8000}:8000"
    # Act
    public = _published_on_public_interface(entry)
    # Assert
    assert public, (
        "the parser failed to flag a ports entry with no interface prefix, "
        "which binds 0.0.0.0 -- so the sweep cannot see the very bug it exists for"
    )


@pytest.mark.parametrize(
    "entry",
    [
        "127.0.0.1:${SCITEX_HUB_HTTP_PORT_DEV:-8000}:8000",
        "127.0.0.1:8000:8000",
        {"target": 8000, "published": 8000, "host_ip": "127.0.0.1"},
    ],
)
def test_port_parser_accepts_loopback_forms(entry):
    # Arrange -- NEGATIVE CONTROL, including compose's long form. The middle case
    # matters most: "${VAR:-8000}" contains a colon inside the default-value
    # syntax, so a naive colon-count would misread it as an interface.
    # Act
    public = _published_on_public_interface(entry)
    # Assert
    assert not public


@pytest.mark.parametrize(
    "path,service,module,ports",
    _ALL,
    ids=[f"{p.name}::{s}" for p, s, _, _ in _ALL],
)
def test_debug_stack_is_not_published_beyond_loopback(path, service, module, ports):
    # Arrange
    rel = path.relative_to(_REPO_ROOT)
    # Act
    exposed = [p for p in ports if _published_on_public_interface(p)]
    # Assert
    assert exposed == [], (
        f"{rel} service '{service}' runs {module}, which defaults DEBUG=True, "
        f"and publishes {exposed} on every interface. Django's technical 500 "
        f"page then serves settings, SQL, local variables and the environment "
        f"to anyone who can reach the host -- no login required. Bind it to "
        f"loopback and reach it over an SSH tunnel:\n"
        f'    - "127.0.0.1:${{YOUR_PORT_VAR:-8000}}:8000"\n'
        f"See deployment/docker/docker_dev/docker-compose.preview.yml, which "
        f"already does exactly this and says why."
    )
