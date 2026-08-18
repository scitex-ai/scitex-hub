#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``/sw.js`` and ``/manifest.json`` must resolve WITHOUT collectstatic.

These two files are served from the URL ROOT rather than from ``/static/``
because a service worker only gets scope over the paths below the URL it was
served from. That means they do NOT go through the ``/static/`` handler, and so
nothing else in the suite covers them.

They were broken for exactly that reason. ``config/urls.py`` pinned their
document root to ``settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]``, and
``STATIC_ROOT`` is a ``Path`` — always truthy, whether or not the directory
exists — so the source-tree fallback was unreachable and both routes pointed at
the collectstatic DESTINATION unconditionally. Any environment that had not run
collectstatic 404'd.

Nothing surfaced it, because ``pwa-register.ts`` registers with
``.catch(() => {})`` and the browser fetches a service-worker script outside the
document's own network context: no broken layout, no failed request in the
page's own network log. It took a console-error capture (run 32059143367 — a
job that went green while recording it) to see the defect at all:

    console.error: A bad HTTP response code (404) was received when
                   fetching the script.

...on 10 of the 11 captured pages.

So the assertions below are deliberately made against an EMPTY ``STATIC_ROOT``.
Pointing them at the real one would let a developer who happens to have run
collectstatic pass a test that CI — and every fresh checkout — fails.
"""

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import resolve

# These tests need database access even though not one of them reads a model,
# and the reason is entirely in the teardown. ``_serve_root_url`` below closes
# the response it was handed — it must, the view returns a ``FileResponse``
# holding an open file handle — and closing ANY ``HttpResponse`` sends the
# global ``request_finished`` signal. Django connects ``close_old_connections``
# to that signal at startup, and that receiver reaches into the connection
# handler. So the DB layer is touched on the way OUT of a request that never
# queried anything.
#
# Unmarked, pytest-django raises out of ``response.close()``:
#
#     RuntimeError: Database access not allowed, use the "django_db" mark, ...
#
# ...before any assertion below runs — which is what happened on PR #655, on
# all three pytest-matrix legs. It reproduces only mid-suite:
# ``close_if_unusable_or_obsolete`` short-circuits unless a connection is
# already open, so an earlier django_db test in the same worker process is
# what arms it, and running this file alone hides the defect.
pytestmark = pytest.mark.django_db


@pytest.fixture
def uncollected_static_root(tmp_path):
    """Point STATIC_ROOT at an empty directory.

    This is the state of every checkout that has not run collectstatic —
    which is what CI, `manage.py runserver` and the test suite all are.
    """
    with override_settings(STATIC_ROOT=str(tmp_path / "staticfiles")):
        yield


def _serve_root_url(url: str) -> tuple[int, bytes, str]:
    """Drive the REAL route for ``url``; return (status, body, content_type).

    Resolved out of the real urlconf rather than re-derived, so the test covers
    the routing as shipped. Called directly instead of through the test client,
    which means a missing file arrives as an ``Http404`` exception (there is no
    exception middleware here to convert it) — normalised to a 404 status so the
    caller can assert on one thing.

    Calling the view directly does NOT make this database-free: see the
    ``pytestmark`` at the top of the module for why ``response.close()`` below
    still needs the ``django_db`` mark.
    """
    match = resolve(url)
    request = RequestFactory().get(url)
    try:
        response = match.func(request, *match.args, **match.kwargs)
    except Http404:
        return 404, b"", ""

    try:
        if getattr(response, "streaming", False):
            body = b"".join(response.streaming_content)
        else:
            body = response.content
        return response.status_code, body, response.headers.get("Content-Type", "")
    finally:
        response.close()


def test_service_worker_is_served_without_collectstatic(uncollected_static_root):
    # Arrange: the fixture has already emptied STATIC_ROOT.
    url = "/sw.js"
    # Act
    status, _body, _content_type = _serve_root_url(url)
    # Assert
    assert status == 200, (
        f"{url} returned {status} with an uncollected STATIC_ROOT — the "
        "staticfiles fallback did not resolve it, so service-worker "
        "registration fails on every page"
    )


def test_manifest_is_served_without_collectstatic(uncollected_static_root):
    # Arrange: the fixture has already emptied STATIC_ROOT.
    url = "/manifest.json"
    # Act
    status, _body, _content_type = _serve_root_url(url)
    # Assert
    assert status == 200, (
        f"{url} returned {status} with an uncollected STATIC_ROOT — the "
        "staticfiles fallback did not resolve it"
    )


def test_service_worker_body_is_not_empty(uncollected_static_root):
    # Arrange: the fixture has already emptied STATIC_ROOT.
    url = "/sw.js"
    # Act
    _status, body, _content_type = _serve_root_url(url)
    # Assert
    assert body.strip(), f"{url} served an empty body — a 200 that installs nothing"


def test_service_worker_is_served_with_a_javascript_mime_type(uncollected_static_root):
    """A wrong Content-Type fails registration as surely as a 404 does.

    Browsers refuse to install a service worker whose script is not served with
    a JavaScript MIME type, and the console error is a DIFFERENT string — so a
    regression here would read as a brand-new bug rather than this one
    returning.
    """
    # Arrange: the fixture has already emptied STATIC_ROOT.
    url = "/sw.js"
    # Act
    _status, _body, content_type = _serve_root_url(url)
    # Assert
    assert "javascript" in content_type.lower(), (
        f"{url} served as {content_type!r}; browsers reject a service worker "
        "that is not served with a JavaScript MIME type"
    )


# EOF
