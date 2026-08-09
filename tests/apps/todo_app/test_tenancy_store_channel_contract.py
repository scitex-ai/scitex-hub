#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which channel carries tenancy to the board — and why both must stay.

Companion to ``test_tenancy_middleware.py``, which covers WHAT the
middleware resolves. This file covers the narrower question of WHICH
CHANNEL that value travels on, because that is the part a reader can
talk themselves out of.

WHY THIS FILE EXISTS
--------------------
``middleware.py`` writes the resolved store to two places: the request
ATTRIBUTE (``request.scitex_store``) and the query parameter
(``request.GET["store"]``). The query write is labelled "LEGACY CHANNEL"
there and "legacy" in the companion tests, and it carries a comment
saying to delete it once the upstream honours the attribute.

On 2026-08-09 that deletion was one edit away from being made. The
reasoning was sound and the conclusion was wrong, because it was drawn
from the upstream's DEVELOP branch. Measured by content in the RUNNING
production container instead (``scitex-hub-prod-django-1``,
``scitex_cards`` 0.32.1, imported from ``/app/.apps/scitex-todo/src``):

    _django/_request_store.py                 DOES NOT EXIST

    _django/views.py:25-27
        def _tasks_path_from_request(request):
            \"\"\"Optional explicit store path from the ``?store=`` query param.\"\"\"
            return request.GET.get("store") or None
        callers: views.py:240, views.py:256, views.py:329 -> get_board(...)

    _django/handlers/dm.py:108
        return getattr(request, STORE_REQUEST_ATTR, None)

    grep STORE_REQUEST_ATTR|scitex_store across _django/ -> ONLY dm.py.

So on the DEPLOYED upstream the attribute is honoured by the DM handler
alone. The BOARD read path has no attribute support at all. The query
parameter is not a vestige there — it is the only channel carrying
tenancy to every board read, and removing it drops the board to the
upstream's ambient canonical store: one store for ALL tenants.

WHAT WOULD MAKE IT SAFE TO DELETE
---------------------------------
Not a version number, and not the develop branch. Read
``views._tasks_path_from_request`` out of the RUNNING container and
confirm it prefers the request attribute. Until that is true in the
deployed code, both channels stay. A comment saying so already existed
at ``middleware.py:200-208`` and was not enough — hence these tests.

Real Django test DB via ``django.test.TestCase`` — no mocks.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project
from apps.workspace.todo_app.middleware import (
    _TODO_INSTALLED,
    TodoBoardTenancyMiddleware,
)

pytestmark = pytest.mark.skipif(
    not _TODO_INSTALLED, reason="scitex-todo not installed"
)


def _run(request):
    """Run the middleware, capturing BOTH channels as the view sees them.

    ``getlist`` as well as ``get``: a consumer reading the first of two
    values sees something ``get`` (which returns the LAST) would hide.
    """
    captured = {}

    def get_response(req):
        captured["query_store"] = req.GET.get("store")
        captured["query_store_list"] = req.GET.getlist("store")
        captured["attr_store"] = getattr(req, "scitex_store", None)
        captured["called"] = True
        return HttpResponse("ok")

    response = TodoBoardTenancyMiddleware(get_response)(request)
    return response, captured


def _get(rf, user, query=""):
    """An authenticated board GET, with an optional RAW query string."""
    request = rf.get(f"/apps/cards/{query}")
    request.user = user
    request.session = {}
    return request


class BoardStoreQueryChannelIsRequiredTest(TestCase):
    """The query channel is load-bearing on the deployed upstream.

    Every assertion here fails if ``middleware.py``'s query injection is
    removed while the deployed upstream still reads ``?store=``. That is
    the point: the failure is the barrier.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice")
        Project.objects.create(owner=cls.alice, name="Proj A", slug="proj-a")

    def setUp(self):
        self.rf = RequestFactory()

    def test_board_get_carries_a_store_on_the_query_channel(self):
        # Arrange — upstream views._tasks_path_from_request reads ONLY this.
        request = _get(self.rf, self.alice)
        # Act
        _, captured = _run(request)
        # Assert
        assert captured["query_store"] is not None

    def test_query_channel_store_is_the_requesting_users_workspace(self):
        # Arrange — a present-but-wrong value is the cross-tenant read.
        request = _get(self.rf, self.alice)
        alice_base = Path(settings_base()) / "data" / "users" / "alice" / "proj"
        # Act
        _, captured = _run(request)
        # Assert
        assert Path(captured["query_store"]).is_relative_to(alice_base)

    def test_both_channels_carry_the_same_store(self):
        # Arrange — the DM handler reads the attribute, the board reads the
        # query; a divergence means the two see different tenants.
        request = _get(self.rf, self.alice)
        # Act
        _, captured = _run(request)
        # Assert
        assert captured["query_store"] == str(captured["attr_store"])


class BoardStoreQueryChannelRejectsSmugglingTest(TestCase):
    """A hostile ``?store=`` is REPLACED, not merely out-voted.

    The middleware logs "discarding client-supplied ?store=" but the log
    line only logs; the actual discard is the assignment that overwrites
    it. These lock the overwrite's semantics, including the repeated-key
    form the single-value tests in the companion file cannot reach.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice")
        Project.objects.create(owner=cls.alice, name="Proj A", slug="proj-a")

    def setUp(self):
        self.rf = RequestFactory()

    def test_repeated_store_params_collapse_to_one_value(self):
        # Arrange — QueryDict.__setitem__ replaces ALL values for the key.
        # An append-style injection would leave the hostile value readable
        # by any consumer using getlist()[0]; get() alone would hide it.
        request = _get(
            self.rf, self.alice, query="?store=/etc/passwd&store=/evil"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert len(captured["query_store_list"]) == 1

    def test_no_smuggled_value_survives_on_the_query_channel(self):
        # Arrange
        request = _get(
            self.rf, self.alice, query="?store=/etc/passwd&store=/evil"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert not {"/etc/passwd", "/evil"} & set(captured["query_store_list"])

    def test_smuggled_values_never_reach_the_attribute_channel(self):
        # Arrange
        request = _get(
            self.rf, self.alice, query="?store=/etc/passwd&store=/evil"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert str(captured["attr_store"]).startswith(str(settings_base()))

    def test_surviving_value_is_still_the_users_own_workspace(self):
        # Arrange — the positive control: proving the hostile values are
        # gone is worthless if the replacement is empty or someone else's.
        request = _get(
            self.rf, self.alice, query="?store=/etc/passwd&store=/evil"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert "/users/alice/proj/" in captured["query_store"]

    def test_other_query_params_are_preserved(self):
        # Arrange — the overwrite must touch `store` and nothing else, or
        # it silently breaks the board's own filters.
        request = _get(
            self.rf, self.alice, query="?store=/etc/passwd&scope=agent:x"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert request.GET.get("scope") == "agent:x"


def settings_base():
    """``settings.BASE_DIR`` — imported late so module import stays cheap."""
    from django.conf import settings

    return settings.BASE_DIR


# EOF
