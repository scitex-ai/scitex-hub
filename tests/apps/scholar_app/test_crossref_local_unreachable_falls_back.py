"""An unreachable crossref-local server must not turn search into an HTTP 500.

"Crossref (SciTeX)" is the only source checked by default on the Scholar
search page, so a down local API used to leave every search empty.
"""

from __future__ import annotations

import json

from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.test import RequestFactory

from apps.workspace.scholar_app.views.search.api_crossref_local import (
    api_search_crossref_local,
)


def _unreachable_search(query, limit, with_if):
    raise ConnectionError("Cannot connect to API at http://127.0.0.1:9")


def _online_crossref(request):
    return JsonResponse({"status": "success", "source": "crossref", "count": 1})


def test_unreachable_local_server_answers_with_online_crossref_results():
    # Arrange
    request = RequestFactory().get(
        "/apps/scholar/api/search/crossref-local/",
        {"q": "sharp wave ripples", "ignore_cache": "true"},
    )
    request.user = AnonymousUser()

    # Act
    response = api_search_crossref_local(
        request, _search=_unreachable_search, _online_fallback=_online_crossref
    )

    # Assert
    assert (response.status_code, json.loads(response.content)["source"]) == (
        200,
        "crossref",
    )
