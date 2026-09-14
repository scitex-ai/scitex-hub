#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_home_dock_redesign.py
"""Home + site dock redesign (operator, 2026-09-14, card
hub-launcher-icons-settings-app-dock-20260914).

What the operator decided, and what each test below pins:
  * ONE dock on EVERY page, rendered from the base template (and injected into
    leaf-app pages that do not use it). The old dock lived only in the launcher
    template, vanished everywhere else, and its "Files" button did not open My
    Projects.
  * Icons only; Home, My Projects, Chat, App Store; Back / Forward at the ends.
  * No header "Apps" dropdown: the logo and the dock are the way Home.
  * Icons: Cards fa-list-check, Storage fa-database, App Store the grid,
    My/Public Projects the same folder (Public with a globe badge).
  * New Settings and Chat tiles.
  * Home pages with dots + arrows; the footer scrolls in above the dock.

Real client, real ORM, real templates; no mocks.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.workspace.apps_app.models import AppsModule
from apps.workspace.apps_app.views.launcher_order import DEFAULT_LAUNCHER_ORDER

_WORKSPACE = Path(settings.BASE_DIR) / "apps" / "workspace"


def inject_dock(request, response):
    # Imported at call time so each test reports on its own (a module-level
    # import would turn every test in this file into one collection error).
    from apps.infra.workspace_app.middleware_site_dock import inject_dock as _inject

    return _inject(request, response)


def dock_items(path):
    from apps.infra.workspace_app.site_dock import dock_items as _items

    return _items(path)


def _manifest(app_dir: str) -> dict:
    return json.loads((_WORKSPACE / app_dir / "manifest.json").read_text("utf-8"))


def _launcher_css(name: str) -> str:
    css = (_WORKSPACE / "apps_app/static/apps_app/css/launcher" / name).read_text(
        "utf-8"
    )
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _icon_ratio(css: str, selector_regex: str):
    """The badge width as a fraction of --launcher-icon-size, from its CSS rule."""
    rule = re.search(selector_regex + r"\s*\{([^}]*)\}", css)
    if not rule:
        return None
    width = re.search(
        r"(?<![-\w])width:\s*calc\(var\(--launcher-icon-size[^)]*\)\s*\*\s*([0-9.]+)\)",
        rule.group(1),
    )
    return float(width.group(1)) if width else None


def _site_css(name: str) -> str:
    css = (Path(settings.BASE_DIR) / "static/shared/css/components" / name).read_text(
        "utf-8"
    )
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _dock_html(content: bytes) -> str:
    text = content.decode("utf-8")
    start = text.index('<nav class="site-dock"')
    return text[start : text.index("</nav>", start)]


class _AncestorClasses(HTMLParser):
    """Records, for every element carrying ``target`` class, its ancestors' classes."""

    VOID = {"img", "input", "br", "hr", "meta", "link", "source"}

    def __init__(self, target: str):
        super().__init__()
        self.target = target
        self.stack: list[str] = []
        self.found: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class") or ""
        if self.target in classes.split():
            self.found.append(list(self.stack))
        if tag not in self.VOID:
            self.stack.append(classes)

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()


class SiteDockOnEveryPageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="dock-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_base_template_renders_the_dock_on_public_projects(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b"data-site-dock" in response.content

    def test_base_template_renders_the_dock_on_my_projects(self):
        # Arrange
        url = "/apps/home/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b"data-site-dock" in response.content

    def test_a_hub_page_gets_exactly_one_dock(self):
        # Arrange — the base template renders it; the middleware must not add
        # a second copy.
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert response.content.count(b"<nav class=\"site-dock\"") == 1

    def test_middleware_injects_the_dock_into_a_leaf_page(self):
        # Arrange — a leaf app serves its OWN document, no hub template.
        request = RequestFactory().get("/apps/scholar/v2/")
        request.user = self.user
        response = HttpResponse("<html><body><main>leaf</main></body></html>")
        # Act
        inject_dock(request, response)
        # Assert
        assert b"data-site-dock" in response.content

    def test_middleware_leaves_an_embedded_frame_alone(self):
        # Arrange
        request = RequestFactory().get("/apps/scholar/v2/", HTTP_SEC_FETCH_DEST="iframe")
        request.user = self.user
        response = HttpResponse("<html><body><main>leaf</main></body></html>")
        # Act
        inject_dock(request, response)
        # Assert
        assert b"data-site-dock" not in response.content

    def test_the_dock_stays_on_public_projects(self):
        # Arrange — the reported bug: the dock disappeared on Public Projects.
        url = "/apps/discovery/"
        # Act
        dock = _dock_html(self.client.get(url).content)
        # Assert
        assert 'data-dock-item="projects"' in dock

    def test_dock_projects_button_opens_my_projects(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        dock = _dock_html(self.client.get(url).content)
        # Assert
        assert re.search(
            r'<a href="/apps/home/"\s+class="site-dock-item[^"]*"\s+data-dock-item="projects"',
            dock,
        )

    def test_dock_has_a_grip_labelled_move_dock(self):
        # Operator 2026-09-14: the drag area must be a recognisable grip.
        # Arrange
        dock = _dock_html(self.client.get("/apps/").content)
        # Act
        grip = re.search(r'<button[^>]*data-dock-grabber[^>]*aria-label="([^"]+)"[^>]*>\s*<i class="([^"]+)"', dock)
        # Assert
        assert (grip.group(1), "fa-grip" in grip.group(2)) == ("Move dock", True)

    def test_dock_grip_hit_area_is_at_least_44px(self):
        # Arrange
        css = _site_css("site-dock.css")
        # Act
        rule = re.search(r"\.site-dock-grabber\s*\{([^}]*)\}", css).group(1)
        sizes = [int(v) for v in re.findall(r"min-(?:width|height):\s*(\d+)px", rule)]
        # Assert
        assert len(sizes) == 2 and min(sizes) >= 44

    def test_dock_shows_icons_only(self):
        # Arrange
        dock = _dock_html(self.client.get("/apps/").content)
        # Act
        visible_text = re.sub(r"<[^>]+>", "", dock).strip()
        # Assert — names live in aria-label / title, never as text
        assert visible_text == ""

    def test_dock_home_button_is_the_house(self):
        # Arrange
        items = dock_items("/apps/discovery/")
        # Act
        home = next(item for item in items if item.key == "home")
        # Assert
        assert (home.icon, home.url) == ("fas fa-house", "/apps/")

    def test_dock_projects_icon_is_the_my_projects_tile_icon(self):
        # Operator 2026-09-14: dock buttons show the SAME coloured app icon as
        # their Home tile, not a bare glyph.
        # Arrange
        dock = _dock_html(self.client.get("/apps/").content)
        tile = next(t for t in self.client.get("/apps/").context["tiles"] if t["name"] == "home")
        # Act
        icon = re.search(
            r'data-dock-item="projects".*?<span class="launcher-tile-icon[^"]*" data-tile-category="([^"]+)"',
            dock,
            re.DOTALL,
        )
        # Assert
        assert icon and icon.group(1) == tile["category"]

    def test_dock_store_icon_matches_the_app_store_tile_colour(self):
        # Arrange
        tile = next(t for t in self.client.get("/apps/").context["tiles"] if t["name"] == "store")
        # Act
        store = next(item for item in dock_items("/apps/") if item.key == "store")
        # Assert
        assert store.category == tile["category"]

    def test_dock_loads_the_shared_app_icon_palette(self):
        # Arrange — the dock is on pages that never load the launcher CSS.
        response = self.client.get("/apps/home/")
        # Act
        linked = b"shared/css/components/app-icon.css" in response.content
        # Assert
        assert linked

    def test_dock_width_defaults_to_the_home_panel_width(self):
        # Arrange
        css = _site_css("site-dock.css")
        # Act
        rule = re.search(r"\.site-dock\s*\{([^}]*)\}", css).group(1)
        # Assert
        assert re.search(r"(?<![-\w])width:\s*var\(--site-dock-width\)", rule)

    def test_anonymous_landing_has_no_dock(self):
        # GUARD (passes on develop by design): every dock target requires
        # sign-in, so the marketing landing must never grow a dock.
        # Arrange
        self.client.logout()
        # Act
        response = self.client.get("/landing/")
        # Assert
        assert b"data-site-dock" not in response.content

    def test_signed_in_logo_goes_home_on_every_page(self):
        # The logo used to point signed-in users at /landing/ everywhere but
        # the landing page. The operator's brief: the logo is the way Home.
        # Arrange
        url = "/apps/discovery/"
        # Act
        content = self.client.get(url).content
        # Assert
        assert re.search(rb'<a href="/apps/"\s+class="header-logo"', content)

    def test_signed_in_logo_goes_home_from_the_landing_page(self):
        # Arrange
        url = "/landing/"
        # Act
        content = self.client.get(url).content
        # Assert
        assert re.search(rb'<a href="/apps/"\s+class="header-logo"', content)

    def test_signed_out_logo_still_points_at_the_landing_page(self):
        # GUARD (passes on develop by design): signed-out visitors keep /landing/.
        # Arrange
        self.client.logout()
        # Act
        content = self.client.get("/pricing/").content
        # Assert
        assert re.search(rb'<a href="/landing/"\s+class="header-logo"', content)

    def test_header_no_longer_renders_the_apps_dropdown(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'id="global-apps"' not in response.content


class ManifestIconTest(TestCase):
    def test_cards_icon_is_list_check(self):
        # Arrange
        app_dir = "todo_app"
        # Act
        icon = _manifest(app_dir)["icon"]
        # Assert
        assert icon == "fas fa-list-check"

    def test_storage_icon_is_database(self):
        # Arrange
        app_dir = "storage_app"
        # Act
        icon = _manifest(app_dir)["icon"]
        # Assert
        assert icon == "fas fa-database"

    def test_app_store_icon_is_the_grid(self):
        # Arrange
        app_dir = "apps_app"
        # Act
        icon = _manifest(app_dir)["icon"]
        # Assert
        assert icon == "fas fa-table-cells-large"

    def test_my_and_public_projects_share_one_folder_icon(self):
        # Arrange
        mine, public = _manifest("repo_app"), _manifest("discovery_app")
        # Act
        icons = {mine["icon"], public["icon"]}
        # Assert
        assert icons == {"fas fa-folder"}

    def test_public_projects_carries_the_globe_badge(self):
        # Arrange
        app_dir = "discovery_app"
        # Act
        badge = _manifest(app_dir).get("icon_badge")
        # Assert
        assert badge == "fas fa-globe"

    def test_projects_tiles_differ_in_colour(self):
        # Arrange
        mine, public = _manifest("repo_app"), _manifest("discovery_app")
        # Act
        categories = (mine.get("category"), public.get("category"))
        # Assert — utility = grey, social = green (launcher/grid.css)
        assert categories == ("utility", "social")


class SettingsAndChatTilesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="link-tiles-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _tiles(self):
        return {t["name"]: t for t in self.client.get("/apps/").context["tiles"]}

    def test_settings_and_chat_are_in_the_launcher_order(self):
        # Arrange
        order = DEFAULT_LAUNCHER_ORDER
        # Act
        chat, tools, settings_ = (
            order.index("chat"),
            order.index("tools"),
            order.index("settings"),
        )
        # Assert — Chat is Work (after Writer, before Tools); Settings leads System
        assert order.index("writer") < chat < tools < settings_ < order.index("docs")

    def test_stats_keeps_its_slot_between_figrecipe_and_writer(self):
        # Arrange
        order = DEFAULT_LAUNCHER_ORDER
        # Act
        slot = order.index("stats")
        # Assert
        assert order.index("figrecipe") < slot < order.index("writer")

    def test_settings_tile_opens_account_settings(self):
        # Arrange
        tiles = self._tiles()
        # Act
        tile = tiles["settings"]
        # Assert
        assert (tile["launch_url"], tile["icon_fa"]) == (
            "/accounts/settings/",
            "fas fa-gear",
        )

    def test_chat_tile_opens_the_dock_chat_route(self):
        # Arrange
        dock_chat = next(item for item in dock_items("/apps/") if item.key == "chat")
        # Act
        tile = self._tiles()["chat"]
        # Assert
        assert tile["launch_url"] == dock_chat.url == "/chat/"

    def test_settings_tile_url_resolves(self):
        # Arrange
        url = self._tiles()["settings"]["launch_url"]
        # Act
        response = self.client.get(url, follow=True)
        # Assert
        assert response.status_code == 200

    def test_link_tiles_are_marked_link_only(self):
        # Arrange
        url = "/apps/"
        # Act
        response = self.client.get(url)
        # Assert — the popover drops Pin / Details for these
        assert response.content.count(b'data-link-only="1"') == 2

    def test_dragged_link_tile_position_persists(self):
        # Arrange — a user reorders from the grid, which has been loaded (and
        # has seeded the catalogue). Within the System group, drop App Store in
        # front of Settings (reorder stays within a group).
        self.client.get("/apps/")
        order = ["home", "discovery", "scholar", "chat", "store", "docs", "settings"]
        # Act
        self.client.post(
            "/apps/store/api/reorder/",
            data=json.dumps({"order": order}),
            content_type="application/json",
        )
        names = [t["name"] for t in self.client.get("/apps/").context["tiles"]]
        # Assert
        assert names.index("store") < names.index("docs") < names.index("settings")

    def test_a_saved_order_never_moves_an_app_into_another_group(self):
        # Arrange — a stale / hand-made order that puts Settings first.
        self.client.get("/apps/")
        order = ["settings", "home", "discovery"]
        # Act
        self.client.post(
            "/apps/store/api/reorder/",
            data=json.dumps({"order": order}),
            content_type="application/json",
        )
        names = [t["name"] for t in self.client.get("/apps/").context["tiles"]]
        # Assert — Settings stays in System, after every Work app
        assert names.index("settings") > names.index("writer")



# EOF
