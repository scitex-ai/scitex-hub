#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A hub deployment has somewhere to state which card store the board reads.

THE DEFECT THESE GUARD. Operator, Telegram 2026-08-17: 「cards が読み込めていない。」
``https://scitex.ai/apps/cards/graph`` answered HTTP 500 and rendered 0 images.
Measured on this branch against the real URLconf with a signed-in user, the
traceback is::

    scitex_cards/_django/views.py:432    in api_dispatch
    scitex_cards/_django/services.py:411 in get_board
    scitex_cards/_store_write.py:184     in store_generation
    scitex_cards/_store_target.py:141    in resolve_store_target
    scitex_cards/_store_target.py:190    in refuse_zero_config_default
    scitex_cards._store_target.StoreTargetNotConfigured: REFUSING to serve:
        no store target is configured ...

The board reads a store the HUB NEVER CONFIGURED. Verified with two
independent readers (``rg --no-ignore`` and ``git grep``, because ``.env*`` is
gitignored and a plain ``rg`` would have reported a false absence): before this
change NOTHING in ``config/``, ``deployment/`` or ``scripts/`` set
``$SCITEX_CARDS_DB`` or the scitex-cards ``store.target`` key, on any
environment. There was no wrong value to fix — there was no place to put one.

WHAT IS UNDER TEST is the configuration seam, not a value. The hub states the
target under its own ``SCITEX_HUB_*`` prefix (ADR-0001, ``config/_env.py``) in
``deployment/docker/envs/.env.<env>`` — the same shape
``SCITEX_HUB_CROSSREF_DB_PATH`` -> ``CROSSREF_DB_PATH`` already has — and
``publish_cards_store_target`` hands it to the package under the name the
package reads.

THE SECOND DEFECT, AND THE REVERSAL — 2026-08-30. The seam above gave a
deployment a PLACE to state the target, and then nobody stated one: measured on
every hub deployment, neither variable was set, so the unconfigured path was
the ONLY path and the board 404'd for everyone. Requiring configuration to
reach the normal path had made the correct setup the exceptional one. The
operator ruled that the fleet's PostgreSQL on 55432 is the DEFAULT and
configuration exists only to OVERRIDE it, so the final tier now resolves
through ``scitex_dev.store.host_store``.

NO LITERAL DSN IS ASSERTED ANYWHERE HERE, and that has not changed. The
abolished 2026-08-13 fallback invented a local FILENAME nobody chose — a
private file that served a store frozen eight days earlier while the fleet
wrote elsewhere, looking healthy throughout. Asking the fleet primitive is the
opposite of inventing a name: ``host_store`` honours ``$SCITEX_STORE_DSN``, has
no file-backed tier, and raises when the fleet store is not durable. So these
tests pin the SHAPE and the SOURCE (``test_no_dsn_is_spelled_out_...``), never
a value.

No mocks: every test drives the real ``publish_cards_store_target``, the real
``optional_upstream_apps`` mount path, and the real upstream resolver. The env
vars are set on the real ``os.environ`` by a fixture that restores them.
"""

from __future__ import annotations

import os
from importlib.util import find_spec
from pathlib import Path

import pytest

from config.settings import _optional_apps
from config.settings._optional_apps import (
    CARDS_STORE_HUB_ENV,
    CARDS_STORE_UPSTREAM_ENV,
    optional_upstream_apps,
    publish_cards_store_target,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_TEMPLATE = REPO_ROOT / "deployment" / "docker" / "envs" / ".env.example"

#: A DSN shaped like the fleet convention (per-host PostgreSQL on 55432) but
#: pointed at a database name no host serves, so a test that accidentally
#: CONNECTS fails loudly instead of reading somebody's real board.
_FAKE_DSN = "postgresql://scitex_cards@127.0.0.1:55432/test_not_a_real_store"
_OTHER_DSN = "postgresql://scitex_cards@127.0.0.1:55432/test_some_other_store"

_DEFECT = (
    "/apps/cards/graph answered HTTP 500 because no hub deployment set a "
    "cards store target anywhere in config/, deployment/ or scripts/, so "
    "scitex_cards.resolve_store_target(None) raised "
    "StoreTargetNotConfigured (operator TG 2026-08-17, CI run 32059143367)."
)

_UNCONFIGURED_DEFECT = (
    "A hub that configured no cards store reached NO store at all: "
    "publish_cards_store_target returned None, so scitex_cards raised "
    "StoreTargetNotConfigured and /apps/cards/* served 404. Measured "
    "2026-08-30: neither SCITEX_HUB_CARDS_STORE nor SCITEX_CARDS_DB was set "
    "in any hub deployment, i.e. the unconfigured path WAS the only path. "
    "Configuration must exist to OVERRIDE the fleet default, never to enable "
    "it (operator ruling 2026-08-30)."
)

_CARDS_INSTALLED = find_spec("scitex_cards") is not None
_requires_cards = pytest.mark.skipif(
    not _CARDS_INSTALLED,
    reason="scitex-cards not installed; the board is not mounted",
)


#: The variable ``scitex_dev.store.host_store`` reads FIRST. Setting it is how
#: a test pins what the fleet default resolves to without depending on the
#: machine running the test having a live fleet PostgreSQL.
_STORE_DSN_ENV = "SCITEX_STORE_DSN"


@pytest.fixture
def fleet_dsn():
    """REAL process env: the fleet store redirected to a known target.

    Tier 3 resolves through ``host_store``, whose FIRST step is
    ``$SCITEX_STORE_DSN``. Pointing that at a known DSN makes the default
    deterministic on a laptop, in CI and on a fleet host alike — and it is the
    production code path, not a stand-in for it: if tier 3 ever stopped going
    through ``host_store``, this value would stop being honoured and the tests
    using it would fail, which is exactly what they are for.
    """
    saved = {
        key: os.environ.get(key)
        for key in (_STORE_DSN_ENV, CARDS_STORE_HUB_ENV, CARDS_STORE_UPSTREAM_ENV)
    }
    os.environ.pop(CARDS_STORE_HUB_ENV, None)
    os.environ.pop(CARDS_STORE_UPSTREAM_ENV, None)
    os.environ[_STORE_DSN_ENV] = _FAKE_DSN
    yield _FAKE_DSN
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def unresolvable_fleet_store():
    """REAL process env: a fleet store target that genuinely cannot resolve.

    ``host_store`` REFUSES a ``$SCITEX_STORE_DSN`` that is not a PostgreSQL
    DSN (``_host.py``: "is not a Postgres DSN"), so this reproduces the
    unresolvable case with the real primitive raising its real exception. No
    production internals are rewritten — the value is bad, and the code under
    test meets it exactly as it would in a misconfigured deployment.
    """
    saved = {
        key: os.environ.get(key)
        for key in (_STORE_DSN_ENV, CARDS_STORE_HUB_ENV, CARDS_STORE_UPSTREAM_ENV)
    }
    os.environ.pop(CARDS_STORE_HUB_ENV, None)
    os.environ.pop(CARDS_STORE_UPSTREAM_ENV, None)
    os.environ[_STORE_DSN_ENV] = "/var/lib/not-a-dsn"
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def hub_store_only():
    """REAL process env: the hub name set, the package's own name absent.

    A deployment that stated its target the hub way and has never heard of
    the package's private variable spelling — which is the entire point of
    the seam. Restored on teardown so ordering cannot leak.
    """
    saved = {
        key: os.environ.get(key)
        for key in (CARDS_STORE_HUB_ENV, CARDS_STORE_UPSTREAM_ENV)
    }
    os.environ.pop(CARDS_STORE_UPSTREAM_ENV, None)
    os.environ[CARDS_STORE_HUB_ENV] = _FAKE_DSN
    yield _FAKE_DSN
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.mark.guards(defect=_DEFECT)
def test_the_hub_setting_is_returned_as_the_target_in_effect():
    # Arrange — a deployment that stated its target the hub way.
    env = {CARDS_STORE_HUB_ENV: _FAKE_DSN}
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published == _FAKE_DSN


@pytest.mark.guards(defect=_DEFECT)
def test_the_hub_setting_is_published_under_the_packages_own_name():
    # Arrange — the package reads $SCITEX_CARDS_DB and nothing else; a hub
    # setting nobody translates is a setting that changes nothing.
    env = {CARDS_STORE_HUB_ENV: _FAKE_DSN}
    # Act
    publish_cards_store_target(env)
    # Assert
    assert env[CARDS_STORE_UPSTREAM_ENV] == _FAKE_DSN


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_production_never_falls_through_to_the_fleet_store(fleet_dsn, caplog):
    """The parent card's prohibition, as a gate: on scitex.ai, "nothing
    configured" must NOT mean "the fleet's board". The board gates on
    is_authenticated only, so tier 3 in production would hand every agent's
    cards and DMs to any signed-in customer. Measured on prod 2026-09-03: all
    three variables unset, so only the container's failure to resolve
    scitex-primary stood between the two — DNS is not a gate."""
    import logging

    for spelling in ("prod", "production", "PROD"):
        env: dict[str, str] = {"SCITEX_HUB_ENV": spelling}
        with caplog.at_level(logging.ERROR):
            published = publish_cards_store_target(env)
        assert published is None, spelling
        assert CARDS_STORE_UPSTREAM_ENV not in env, spelling
        assert any("PRODUCTION" in r.getMessage() for r in caplog.records), spelling
        caplog.clear()


def test_production_still_honours_a_store_the_deployment_owns():
    """The gate blocks the DEFAULT, not the deployment's choice: tier 2 on
    production publishes exactly as it does anywhere else."""
    env: dict[str, str] = {"SCITEX_HUB_ENV": "prod", CARDS_STORE_HUB_ENV: _FAKE_DSN}
    published = publish_cards_store_target(env)
    assert published == _FAKE_DSN
    assert env[CARDS_STORE_UPSTREAM_ENV] == _FAKE_DSN


def test_development_and_staging_still_reach_the_fleet_default(fleet_dsn):
    """Negative control for the gate: the environments tier 3 exists for keep
    getting it, under every spelling settings/__init__.py accepts."""
    for spelling in ("development", "dev", "staging", "stag", ""):
        env: dict[str, str] = {"SCITEX_HUB_ENV": spelling} if spelling else {}
        assert publish_cards_store_target(env) == fleet_dsn, spelling


def test_the_fleet_store_is_reached_when_nobody_configured_one(fleet_dsn):
    # Arrange — the state every hub deployment was in, measured 2026-08-30:
    # neither variable set anywhere, so the resolver raised and
    # /apps/cards/graph served HTTP 500. Requiring a variable to reach the
    # normal path made the CORRECT configuration the exceptional one.
    env: dict[str, str] = {}
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published == fleet_dsn


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_the_fleet_default_is_published_under_the_packages_own_name(fleet_dsn):
    # Arrange — publishing is the whole mechanism: the package reads
    # $SCITEX_CARDS_DB and nothing else.
    env: dict[str, str] = {}
    # Act
    publish_cards_store_target(env)
    # Assert
    assert env[CARDS_STORE_UPSTREAM_ENV] == fleet_dsn


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_the_default_is_the_fleet_postgres_not_a_local_file(fleet_dsn):
    # Arrange — the abolished fallback invented a local FILENAME nobody
    # chose: private, per-process, silently divergent. This default is the
    # opposite: it asks scitex_dev.store.host_store, the fleet's single
    # source of truth, which has no file-backed tier at all. Assert the
    # SHAPE, never this repo's own literal — pinning a DSN here would
    # re-create the hardcoded default the indirection exists to avoid.
    env: dict[str, str] = {}
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published.startswith(("postgres://", "postgresql://"))


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_an_unresolvable_fleet_store_does_not_abort_settings_import(
    unresolvable_fleet_store,
):
    # Arrange — publish_cards_store_target runs at SETTINGS LOAD. A host
    # where the fleet store cannot be resolved must lose the BOARD, not the
    # whole site: raising here takes down the landing page, auth and every
    # unrelated app over one leaf's database. PR #689 ruled on that shape.
    env: dict[str, str] = {}
    # Act — the real host_store refusing a real bad value; must not raise.
    published = publish_cards_store_target(env)
    # Assert
    assert published is None


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_an_unresolvable_fleet_store_invents_no_substitute(
    unresolvable_fleet_store,
):
    # Arrange — degrading is allowed; guessing is not. Nothing may be
    # published when the real target could not be resolved.
    env: dict[str, str] = {}
    # Act
    publish_cards_store_target(env)
    # Assert
    assert CARDS_STORE_UPSTREAM_ENV not in env


@pytest.mark.guards(defect=_UNCONFIGURED_DEFECT)
def test_no_dsn_is_spelled_out_in_the_settings_module():
    # Arrange — the guard that replaces the old "invent nothing" one. The
    # default must come from the primitive, so a literal fleet DSN written
    # into this module would drift the moment the fleet moved.
    source = (
        Path(_optional_apps.__file__).read_text(encoding="utf-8").splitlines()
    )
    # Act — ignore prose; a DSN in a docstring is documentation, not wiring.
    code = [ln for ln in source if "postgresql://" in ln and not ln.lstrip().startswith("#")]
    # Assert
    assert not [ln for ln in code if "55432" in ln]


@pytest.mark.guards(defect=_DEFECT)
def test_an_explicit_upstream_target_is_never_overridden():
    # Arrange — exporting the package's own variable says something MORE
    # specific than the deployment did; overwriting it moves that process
    # to a different store without telling anyone.
    env = {
        CARDS_STORE_UPSTREAM_ENV: _FAKE_DSN,
        CARDS_STORE_HUB_ENV: _OTHER_DSN,
    }
    # Act
    publish_cards_store_target(env)
    # Assert
    assert env[CARDS_STORE_UPSTREAM_ENV] == _FAKE_DSN


@pytest.mark.guards(defect=_DEFECT)
@pytest.mark.parametrize(
    "env",
    [
        {CARDS_STORE_HUB_ENV: ""},
        {CARDS_STORE_UPSTREAM_ENV: "", CARDS_STORE_HUB_ENV: ""},
    ],
    ids=["hub-empty", "both-empty"],
)
def test_an_empty_value_counts_as_unset(env, fleet_dsn):
    # Arrange — `SCITEX_HUB_CARDS_STORE=` in a .env file is common, and the
    # resolver's own test is `if value:`. An empty value must fall THROUGH to
    # the fleet default, exactly as an absent one does; publishing the empty
    # string itself would mean something different here than it does one call
    # downstream, and would hand the package a target it rejects.
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published


@_requires_cards
@pytest.mark.guards(defect=_DEFECT)
def test_mounting_the_board_publishes_the_target(hub_store_only):
    # Arrange — the wiring is what matters: a publish function nobody calls
    # fixes nothing, and the mount is the moment the store becomes required.
    expected = hub_store_only
    # Act
    optional_upstream_apps()
    # Assert
    assert os.environ[CARDS_STORE_UPSTREAM_ENV] == expected


@_requires_cards
@pytest.mark.guards(defect=_DEFECT)
def test_the_board_is_actually_among_the_mounted_apps(hub_store_only):
    # Arrange — the assertion above is vacuous if the cards branch never
    # ran, so the branch itself is pinned separately.
    del hub_store_only
    # Act
    entries = optional_upstream_apps()
    # Assert
    assert any("scitex_cards" in entry for entry in entries), entries


@_requires_cards
@pytest.mark.guards(defect=_DEFECT)
def test_the_package_resolver_answers_the_published_target(hub_store_only):
    # Arrange — the end-to-end claim, through the package's own resolver
    # rather than through our belief about which variable it reads. This is
    # the exact call that raised StoreTargetNotConfigured on /apps/cards/graph.
    from scitex_cards._store_target import resolve_store_target

    expected = hub_store_only
    publish_cards_store_target()
    # Act
    resolved = resolve_store_target(None)
    # Assert
    assert resolved == expected


@pytest.mark.guards(defect=_DEFECT)
def test_the_env_template_tells_an_operator_the_variable_exists():
    # Arrange — .env.<env> is gitignored, so the TEMPLATE is the only place
    # a new deployment can learn the name. A seam nobody can find is the
    # same outage as no seam.
    text = ENV_TEMPLATE.read_text(encoding="utf-8")
    # Act
    documented = CARDS_STORE_HUB_ENV in text
    # Assert
    assert documented, ENV_TEMPLATE


@pytest.mark.guards(defect=_DEFECT)
def test_the_template_actually_assigns_the_variable():
    # Arrange — a name mentioned only in a comment leaves the reader to
    # guess the spelling of the assignment.
    text = ENV_TEMPLATE.read_text(encoding="utf-8")
    # Act
    assignments = [
        line
        for line in text.splitlines()
        if line.startswith(f"{CARDS_STORE_HUB_ENV}=")
    ]
    # Assert
    assert assignments, ENV_TEMPLATE


@pytest.mark.guards(defect=_DEFECT)
def test_the_documented_example_uses_the_scitex_postgres_port():
    # Arrange — operator ruling: 5432 is never scitex, and an example inside
    # documentation is read by someone already lost and looking for a line
    # to copy. The fleet convention is a per-host PostgreSQL on 55432.
    text = ENV_TEMPLATE.read_text(encoding="utf-8")
    assignments = [
        line
        for line in text.splitlines()
        if line.startswith(f"{CARDS_STORE_HUB_ENV}=")
    ]
    # Act
    wrong_port = [line for line in assignments if ":5432/" in line]
    # Assert
    assert not wrong_port, wrong_port


# EOF
