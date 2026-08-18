#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The /apps/cards/ mount states its provisioning instead of crashing.

THE DEFECT THESE GUARD. Operator, Telegram 2026-08-17 msg 3466, verbatim:
「cards が読み込めていない。」 CI run 32059143367 (PR #643, head 188dd3a01)
went all-green, 20/20, while its ``content-report.txt`` artifact recorded::

    === Cards (/apps/cards/)
      images ............... 0 rendered, 0 broken, 0 absent runtime media
      browser errors ....... 2
          HTTP 500 http://127.0.0.1:8000/apps/cards/graph

Cards was the only page in the set rendering zero images.

WHY AN ANONYMOUS PROBE DOES NOT SHOW IT, and why these tests log in. Hitting
``https://scitex.ai/apps/cards/graph`` anonymously returns 401 — the auth wall
answering first (``TodoBoardTenancyMiddleware`` shapes a ``signed-out`` JSON
for data fetches). That 401 is not evidence the bug is absent; it is evidence
the request never reached the board. CI reproduces the 500 precisely because
it holds a real pooled-visitor session and gets past the wall. So every test
here drives the REAL URLconf with a logged-in user and a resolvable project.

WHAT ACTUALLY FAILED. The board's card DATA comes from an ambient store the
hub never configures — nothing in ``config/``, ``deployment/`` or ``scripts/``
sets ``$SCITEX_CARDS_DB`` or the scitex-cards ``store.target`` config key.
Since scitex-cards 0.43 that resolver refuses to invent a default::

    File ".../scitex_cards/_django/views.py", line 432, in api_dispatch
    File ".../scitex_cards/_django/services.py", line 411, in get_board
        generation = store_generation(resolved)
    File ".../scitex_cards/_store_write.py", line 185, in store_generation
        if not is_postgres_url(resolve_store_target(None)):
    File ".../scitex_cards/_store_target.py", line 190, in
        refuse_zero_config_default
    scitex_cards._store_target.StoreTargetNotConfigured: REFUSING to serve:
        no store target is configured ...

``StoreTargetNotConfigured`` is a plain ``RuntimeError``, not a
``StoreUnavailableError`` subclass, so upstream's own typed 404-for-absent /
500-for-outage split misses it and it lands in the generic ``except
Exception`` — an HTTP 500 for a permanent configuration state.

Real Django test DB and the real URLconf — no mocks. The environment is set to
the state a CI runner and a fresh deployment are actually in (no store target
chosen); that is the condition under test, not a stand-in for it.
"""

import json
import os
import tempfile
from importlib.util import find_spec

import pytest
from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project

pytestmark = pytest.mark.skipif(
    find_spec("scitex_cards") is None and find_spec("scitex_todo") is None,
    reason="scitex-cards not installed",
)

#: THE WIRE VALUE, WRITTEN OUT, not imported from the middleware. This
#: discriminator is a contract with whatever reads the response; asserting it
#: against the constant that produces it would keep passing through a rename
#: that silently broke every consumer, which is the class of gate that cannot
#: fail. Spelling it here is what makes a rename show up as a red test.
_EXPECTED_REASON = "cards-store-not-configured"

#: Likewise written out rather than imported. This is the name an operator
#: types into a ``.env`` file; asserting it against the constant that renders
#: it would keep passing through a rename that left every deployment reading a
#: variable the hub no longer publishes.
_EXPECTED_SETTING = "SCITEX_HUB_CARDS_STORE"

_DEFECT = (
    "/apps/cards/graph answered HTTP 500 for a signed-in visitor because "
    "scitex-cards' StoreTargetNotConfigured is not a StoreUnavailableError "
    "subclass, so the hub mount crashed through a configuration state "
    "instead of stating it (CI run 32059143367)."
)


class CardsMountStoreProvisioningTest(TestCase):
    """An unconfigured card store is stated, never served as a 500."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice", password="pw")
        Project.objects.create(owner=cls.alice, name="Proj A", slug="proj-a")

    def setUp(self):
        # A runner / fresh deployment with NO store target chosen — the
        # condition CI is in. An EMPTY $SCITEX_CARDS_DB is read as unset by
        # the resolver (`if value:`), and $SCITEX_DIR moves the config tier
        # onto an empty directory so a developer's own configured store
        # cannot mask the defect on their machine.
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = {
            key: os.environ.get(key)
            for key in ("SCITEX_CARDS_DB", "SCITEX_DIR")
        }
        os.environ["SCITEX_CARDS_DB"] = ""
        os.environ["SCITEX_DIR"] = self._tmp.name
        self.client = Client(raise_request_exception=False)
        self.client.force_login(self.alice)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_with_no_store_target_is_not_a_server_error(self):
        # Arrange — a signed-in user with a resolvable project, so the
        # request reaches the board rather than stopping at the auth wall
        # (the 401 that makes an anonymous probe look healthy).
        path = "/apps/cards/graph"
        # Act
        response = self.client.get(path)
        # Assert
        assert response.status_code != 500, response.content[:500]

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_with_no_store_target_answers_not_found(self):
        # Arrange — non-5xx so a real outage stays visible in 5xx
        # monitoring, and non-retryable so the board stops re-polling.
        path = "/apps/cards/graph"
        # Act
        response = self.client.get(path)
        # Assert
        assert response.status_code == 404

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_refusal_carries_the_machine_readable_reason(self):
        # Arrange — the discriminator is what lets the board tell this
        # apart from every other 404 without string-matching prose.
        path = "/apps/cards/graph"
        # Act
        payload = json.loads(self.client.get(path).content)
        # Assert
        assert payload.get("reason") == _EXPECTED_REASON

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_refusal_preserves_the_resolvers_own_sentence(self):
        # Arrange — the reason must survive to whoever is reading it; a
        # fixed replacement sentence would throw away the diagnosis.
        path = "/apps/cards/graph"
        # Act
        payload = json.loads(self.client.get(path).content)
        # Assert
        assert "no store target is configured" in payload.get("error", "")

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_refusal_names_the_hub_variable_to_set(self):
        # Arrange — upstream's sentence names $SCITEX_CARDS_DB and its own
        # config key, neither of which is what a hub operator sets. A
        # correct diagnosis with no reachable action is the failure the
        # constitution names: "name the offending file, value, or version".
        path = "/apps/cards/graph"
        # Act
        payload = json.loads(self.client.get(path).content)
        # Assert
        assert _EXPECTED_SETTING in payload.get("hint", "")

    @pytest.mark.guards(defect=_DEFECT)
    def test_graph_refusal_points_at_the_file_that_holds_the_value(self):
        # Arrange — the variable alone still leaves "set it WHERE?"; the
        # answer is the env file the rest of the deployment already uses.
        path = "/apps/cards/graph"
        # Act
        payload = json.loads(self.client.get(path).content)
        # Assert
        assert "deployment/docker/envs/.env" in payload.get("hint", "")

    @pytest.mark.guards(defect=_DEFECT)
    def test_board_page_with_no_store_target_still_renders(self):
        # Arrange — the page carries its own load-error banner; replacing
        # it with a raw JSON blob would lose that.
        path = "/apps/cards/"
        # Act
        response = self.client.get(path)
        # Assert
        assert response.status_code == 200

    @pytest.mark.guards(defect=_DEFECT)
    def test_dm_threads_with_no_store_target_still_answers(self):
        # Arrange — DM reads the store THIS middleware injected, not the
        # ambient one, and works today; the refusal must not blanket it.
        path = "/apps/cards/dm/threads"
        # Act
        response = self.client.get(path)
        # Assert
        assert response.status_code == 200

    @pytest.mark.guards(defect=_DEFECT)
    def test_ping_with_no_store_target_still_answers(self):
        # Arrange — a health probe that fails on configuration is useless.
        path = "/apps/cards/ping"
        # Act
        response = self.client.get(path)
        # Assert
        assert response.status_code == 200
