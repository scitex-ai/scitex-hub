#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_app_creator_slot.py
"""App Creator is an empty "+" slot, always last in Work (operator, 2026-09-14).

Real client, real ORM, real templates; no mocks.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import translation
from django.utils.translation import trans_real

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAUNCHER_CSS = _REPO_ROOT / "apps/workspace/apps_app/static/apps_app/css/launcher"


@pytest.fixture(name="compiled_catalogs", scope="module")
def _compiled_catalogs():
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    trans_real._translations.clear()
    yield
    trans_real._translations.clear()


def _work_band(html: str) -> str:
    start = html.index('data-group="work" aria-label')
    end = re.compile(r'class="launcher-group" role="group" data-group="(?!work")')
    return html[start : end.search(html, start).start()]


def _cells(html: str) -> list[tuple[str, str]]:
    """(class, data-module) of every grid cell in the Work band, in order."""
    return re.findall(
        r'<a\b[^>]*?class="([^"]*)"[^>]*?data-module="([^"]+)"', _work_band(html)
    )


class AppCreatorSlotTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="app-creator-slot-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _home(self) -> str:
        return self.client.get("/apps/").content.decode("utf-8")

    def test_last_work_cell_is_the_dashed_app_creator_slot(self):
        # Arrange
        url = "/apps/"
        # Act
        last = _cells(self.client.get(url).content.decode("utf-8"))[-1]
        # Assert
        assert last == ("launcher-slot launcher-slot--add", "create-app")

    def test_app_creator_slot_has_no_version_label(self):
        # Arrange
        html = self._home()
        # Act
        start = html.index('data-module="create-app"')
        slot = html[start : html.index("</a>", start)]
        # Assert
        assert "launcher-tile-version" not in slot

    def test_app_creator_slot_is_labelled_app_creator(self):
        # Arrange
        html = self._home()
        # Act
        module = html.index('data-module="create-app"')
        start = html.rindex("<a", 0, module)
        slot = html[start : html.index(">", module)]
        # Assert
        assert (
            'aria-label="App Creator"' in slot
            and 'title="App Creator"' in slot
            and 'draggable="false"' in slot
        )

    def test_app_creator_slot_shows_a_visible_label(self):
        # Arrange
        html = self._home()
        # Act
        start = html.index('data-module="create-app"')
        slot = html[start : html.index("</a>", start)]
        # Assert
        assert '<span class="launcher-slot-add-label">App Creator</span>' in slot

    def test_slot_stays_last_after_the_user_reorders_it_to_the_front(self):
        # Operator iPhone 2026-09-14: 1000+ reorder values put it FIRST in Work.
        # Arrange
        self.client.post(
            "/apps/store/api/reorder/",
            data=json.dumps({"order": ["create-app", "tools", "writer", "scholar"]}),
            content_type="application/json",
        )
        # Act
        cells = self.client.get("/apps/").context["groups"][1]["cells"]
        # Assert
        assert cells[-1]["name"] == "create-app"

    def test_slot_cannot_be_saved_into_the_dock(self):
        # Arrange
        body = json.dumps({"dock": ["launcher", "create-app"]})
        # Act
        response = self.client.post(
            "/apps/store/api/dock/", data=body, content_type="application/json"
        )
        # Assert
        assert response.status_code == 400


def test_app_creator_visible_label_is_localized_in_japanese(compiled_catalogs):
    # Arrange
    tile = {
        "label": "App Creator",
        "launch_url": "/apps/store/create/",
        "name": "create-app",
        "group": "work",
    }
    # Act
    with translation.override("ja"):
        html = render_to_string(
            "apps_app/partials/launcher_add_slot.html", {"tile": tile}
        )
    # Assert
    assert (
        '<span class="launcher-slot-add-label">アプリ<wbr>クリエイター</span>' in html
    )


def test_app_creator_label_css_fits_a_four_column_mobile_cell():
    # Arrange
    css = (_LAUNCHER_CSS / "grid.css").read_text(encoding="utf-8")
    mobile = (_LAUNCHER_CSS / "mobile.css").read_text(encoding="utf-8")
    # Act
    columns = set(re.findall(r"--launcher-cols:\s*(\d+)", css + mobile))
    slot_rule = re.search(
        r"\.launcher-slot\.launcher-slot--add\s*\{([^}]*)\}", css
    ).group(1)
    label_match = re.search(r"\.launcher-slot-add-label\s*\{([^}]*)\}", css)
    label_rule = label_match.group(1) if label_match else ""
    # Assert — the link remains a full touch target without widening its grid track.
    assert (
        columns == {"4"}
        and "min-width: 0" in slot_rule
        and "min-height: 44px" in slot_rule
        and "max-width: 100%" in label_rule
    )


# EOF
