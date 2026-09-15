#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy /<app>/ -> /apps/<app>/ 301 redirects (compass L658).

config/urls_legacy_redirects.py generates one permanent redirect per entry in
LEGACY_APP_NAMES. Every live app must be in it, or the bare /<app>/ path falls
through to root_dispatch (the landing page) instead of the clean 301 its
siblings get — the "lands on a legacy shell" trap L658 warns about.

figrecipe was the gap: it is a live app (config/urls.py mounts
/apps/figrecipe/) but was missing from LEGACY_APP_NAMES, so /figrecipe/ went
to the landing page while /scholar/, /writer/, etc. 301'd correctly. This
pins that — and asserts figrecipe behaves like a known-good sibling — so it
cannot silently drop out of the list again.
"""

import pytest
from django.test import Client


@pytest.mark.django_db
class TestLegacyAppPrefixRedirects:
    def test_legacy_figrecipe_prefix_is_a_permanent_redirect(self):
        # Arrange
        http = Client()
        # Act
        response = http.get("/figrecipe/")
        # Assert
        assert response.status_code == 301

    def test_legacy_figrecipe_redirects_to_the_apps_mount(self):
        # Arrange — a 301 to the wrong place would still be a 301.
        http = Client()
        # Act
        response = http.get("/figrecipe/")
        # Assert
        assert response.headers["Location"] == "/apps/figrecipe/"

    def test_legacy_figrecipe_matches_a_known_good_sibling(self):
        # Arrange — /writer/ is an established member of LEGACY_APP_NAMES; if
        # figrecipe's redirect diverges from writer's, the mechanism is
        # inconsistent, not just "a 301 happened".
        http = Client()
        # Act
        fig = http.get("/figrecipe/")
        writer = http.get("/writer/")
        # Assert — same status, and both point at their /apps/ mount.
        assert fig.status_code == writer.status_code == 301
        assert fig.headers["Location"] == "/apps/figrecipe/"
        assert writer.headers["Location"] == "/apps/writer/"
