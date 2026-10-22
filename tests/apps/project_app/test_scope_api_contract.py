#!/usr/bin/env python3
"""Hub project-scope API serves the SDK tagged-scope contract — live-server verified.

Card ui-project-selector-user-scope-option-20260918.
Runs against the container dev server (DB-backed pytest cannot create a
test database here: role lacks CREATEDB). Uses test-user; leaves the
committed selection on a scratch project, restored afterwards.
"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"

_probe = json.dumps({"probe": 1}).encode()


def _login():
    import http.cookiejar
    import os
    import re

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    page = opener.open(BASE + "/auth/signin/", timeout=10).read().decode()
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
    data = urllib.parse.urlencode(
        {
            "csrfmiddlewaretoken": token,
            "username": "test-user",
            "password": os.environ["SCITEX_HUB_TEST_USER_PASSWORD"],
        }
    ).encode()
    opener.open(
        urllib.request.Request(
            BASE + "/auth/signin/", data=data, headers={"Referer": BASE + "/auth/signin/"}
        ),
        timeout=15,
    )
    return opener


import urllib.parse  # noqa: E402  (kept after helper for readability)


def test_scope_contract_live():
    opener = _login()

    def get():
        response = opener.open(BASE + "/api/project/scope/", timeout=15)
        assert response.status == 200
        return json.loads(response.read())

    def post(payload, want):
        request = urllib.request.Request(
            BASE + "/api/project/scope/",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with opener.open(request, timeout=15) as response:
                body = json.loads(response.read())
                status = response.status
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read())
            status = exc.code
        assert status == want, (payload, status, body)
        return body

    body = get()
    assert body["allow_user_scope"] is True
    assert set(body) >= {"projects", "current", "allow_user_scope"}

    body = post({"scope": "user", "id": None}, 200)
    assert body == {"current": None, "current_scope": "user"}

    body = post({"scope": "project", "id": "test-user/dotfiles"}, 200)
    assert body["current_scope"] == "project"
    assert get()["current_scope"] == "project"

    body = post({"id": "test-user/dotfiles"}, 200)
    assert body["current"] == "test-user/dotfiles"

    post({"scope": "org", "id": "x"}, 403)
    post({"scope": "project", "id": "nobody/ghost"}, 403)
    post({"scope": "user"}, 403)
    post({"scope": "user", "id": 5}, 403)
