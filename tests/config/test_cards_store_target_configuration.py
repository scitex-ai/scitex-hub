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

NO DEFAULT DSN IS ASSERTED ANYWHERE HERE, deliberately. A literal fallback is
the silent-fallback failure upstream abolished on 2026-08-13 after one served a
store frozen eight days earlier while the fleet wrote elsewhere, looking
healthy throughout. ``test_nothing_is_invented_...`` pins that: the
unconfigured state must stay unconfigured, and be REPORTED — see
``tests/apps/todo_app/test_cards_mount_store_provisioning.py``.

No mocks: every test drives the real ``publish_cards_store_target``, the real
``optional_upstream_apps`` mount path, and the real upstream resolver. The env
vars are set on the real ``os.environ`` by a fixture that restores them.
"""

from __future__ import annotations

import os
from importlib.util import find_spec
from pathlib import Path

import pytest

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

_CARDS_INSTALLED = find_spec("scitex_cards") is not None
_requires_cards = pytest.mark.skipif(
    not _CARDS_INSTALLED,
    reason="scitex-cards not installed; the board is not mounted",
)


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


@pytest.mark.guards(defect=_DEFECT)
def test_nothing_is_reported_when_nobody_configured_one():
    # Arrange — the state every hub deployment was in before this change.
    env: dict[str, str] = {}
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published is None


@pytest.mark.guards(defect=_DEFECT)
def test_no_store_is_invented_when_nobody_configured_one():
    # Arrange — a literal default here would be the silent fallback that
    # served a store frozen eight days earlier and looked healthy.
    env: dict[str, str] = {}
    # Act
    publish_cards_store_target(env)
    # Assert
    assert CARDS_STORE_UPSTREAM_ENV not in env


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
def test_an_empty_value_counts_as_unset(env):
    # Arrange — `SCITEX_HUB_CARDS_STORE=` in a .env file is common, and the
    # resolver's own test is `if value:`. Publishing an empty string would
    # mean something different here than it does one call downstream.
    expected = None
    # Act
    published = publish_cards_store_target(env)
    # Assert
    assert published == expected


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
