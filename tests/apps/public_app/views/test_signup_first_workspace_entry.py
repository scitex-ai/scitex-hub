#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signed-out browsers enter workspace apps through signup, never a pool state."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.console_app.workspace_views import code_workspace
from apps.workspace.figrecipe_app.views import figure_editor
from apps.workspace.scholar_app.views.search.page_views import _check_signup_redirect
from apps.workspace.writer_app.views.index.main import index_view


@pytest.fixture
def browser_request():
    request = RequestFactory().get("/apps/example/", HTTP_USER_AGENT="Mozilla/5.0")
    request.user = AnonymousUser()
    return request


@pytest.mark.parametrize(
    "view",
    [figure_editor, index_view, _check_signup_redirect, code_workspace],
)
def test_signed_out_browser_is_sent_to_signup(browser_request, view):
    response = view(browser_request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/signup/"
