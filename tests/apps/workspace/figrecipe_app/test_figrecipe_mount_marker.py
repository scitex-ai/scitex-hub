#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mount-marker injection gate (hub PR #1090 follow-up).

The bundle's mountPrefix() throws (blank page) when the served page
carries no mount marker. The hub wrapper adds it idempotently.
"""

import django
from django.conf import settings


def _configured():
    if not settings.configured:
        settings.configure(
            DEBUG=False,
            ALLOWED_HOSTS=["*"],
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
        )
        django.setup()


_configured()

from django.http import HttpResponse, JsonResponse  # noqa: E402

from apps.workspace.figrecipe_app.urls.figrecipe_django import (  # noqa: E402
    _with_mount_marker,
)


def _page(html):
    def view(request):
        return HttpResponse(html, content_type="text/html")

    return view


def test_added_when_absent():
    out = _with_mount_marker(_page("<html><head></head><body>x</body></html>"))(
        None
    )
    body = out.content.decode()
    assert 'name="stx-mount" content="/apps/figrecipe"' in body
    assert body.count("stx-mount") == 1


def test_byte_identical_when_present():
    html = '<html><head><meta name="stx-mount" content="/apps/figrecipe" /></head></html>'
    out = _with_mount_marker(_page(html))(None)
    assert out.content.decode() == html


def test_single_quote_variant_present():
    html = "<html><head><meta name='stx-mount' content='/apps/figrecipe' /></head></html>"
    out = _with_mount_marker(_page(html))(None)
    assert out.content.decode() == html


def test_non_html_passthrough():
    def view(request):
        return JsonResponse({"ok": True})

    out = _with_mount_marker(view)(None)
    assert out.status_code == 200


def test_no_head_passthrough():
    out = _with_mount_marker(_page("<html><body>x</body></html>"))(None)
    assert b"stx-mount" not in out.content
