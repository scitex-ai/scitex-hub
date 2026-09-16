#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dead links a browser console sweep of the dev site found (2026-09-14).

1. No hub markup may link to /accounts/login/ or /accounts/signup/.
2. The profile editor must fetch its city list from the real static path
   (fixed in #823; the sweep saw the old 404, so it is guarded here too).

Sign-in and sign-up live under /auth/ (apps/infra/auth_app, mounted at
"auth/" in config/urls.py). The /accounts/login/ and /accounts/signup/ paths
are allauth's defaults and are NOT routed here: both return 404. A browser
console sweep of the dev site (2026-09-14) showed the console workspace's
"Sign Up Free" buttons pointing at /accounts/signup/, so a visitor who tried
to keep their work hit a 404 page.

Comments that MENTION the dead path (to warn against it) are allowed; only
link targets are checked.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.urls import reverse

SCANNED_SUFFIXES = {".html", ".ts", ".js"}
SCANNED_ROOTS = ("templates", "apps")
SKIPPED_PARTS = {"node_modules", "dist", "build", "staticfiles", ".vite"}

DEAD_LINK = re.compile(r"""href\s*=\s*["'`]/accounts/(?:login|signup)/""")


def _scanned_files() -> list[Path]:
    root = Path(settings.BASE_DIR)
    files = []
    for top in SCANNED_ROOTS:
        for path in (root / top).rglob("*"):
            if path.suffix not in SCANNED_SUFFIXES:
                continue
            if SKIPPED_PARTS.intersection(path.parts):
                continue
            if ".min." in path.name:
                continue
            files.append(path)
    return files


def _dead_links() -> list[str]:
    root = Path(settings.BASE_DIR)
    offenders = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in DEAD_LINK.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(root)}:{line}")
    return offenders


class TestDeadLinksFoundByConsoleSweep:
    def test_the_signup_route_is_under_auth(self):
        """The replacement target must exist, or the fix points at a 404 too."""
        # Arrange
        name = "auth_app:signup"

        # Act
        path = reverse(name)

        # Assert
        assert path == "/auth/signup/"

    def test_the_pattern_catches_a_dead_link(self):
        """Vacuity check: a regex that matches nothing would pass everything."""
        # Arrange
        sample = '<a href="/accounts/signup/" class="btn">Sign Up</a>'

        # Act
        found = DEAD_LINK.search(sample)

        # Assert
        assert found is not None

    def test_profile_edit_fetches_cities_from_a_real_static_path(self):
        """/static/data/cities_timezones.json 404'd on /accounts/settings/.

        The file lives at static/shared/data/; the hardcoded path skipped the
        `shared/` segment, so the location autocomplete loaded the 404 HTML
        page, logged a JSON SyntaxError to the console, and never suggested a
        city.
        """
        # Arrange
        template = (
            Path(settings.BASE_DIR)
            / "apps/infra/accounts_app/templates/accounts_app/profile_edit.html"
        )

        # Act
        text = template.read_text(encoding="utf-8")

        # Assert
        assert "{% static 'shared/data/cities_timezones.json' %}" in text

    def test_no_markup_links_to_accounts_login_or_signup(self):
        # Arrange
        expected: list[str] = []

        # Act
        offenders = _dead_links()

        # Assert
        assert offenders == expected, (
            f"links to 404ing /accounts/ auth routes: {offenders}. "
            "Use {% url 'auth_app:signup' %} / {% url 'auth_app:login' %}."
        )
