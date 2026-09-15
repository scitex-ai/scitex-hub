#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_home_grid_rows_and_badges.py
"""Home grid rows, pages, edit-mode motion and tile badges (operator, 2026-09-14).

Split from test_home_dock_redesign.py (line budget). Pins:
  * rows of 4 at every width, one group per row, no empty cell for the
    not-yet-built Stats app, and a short group leaving its row's remaining
    cells empty;
  * page arrows hidden on phones;
  * reorder travel 300-350ms, and reduced motion makes the wiggle stop and
    moves instant;
  * badges inside the icon and sized as a fraction of it, desktop-only tiles
    not dimmed, launcher stylesheets cache-busted.

Real client, real ORM, real templates; no mocks.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.infra.workspace_app import registry
from apps.workspace.apps_app.models import AppsModule

_WORKSPACE = Path(settings.BASE_DIR) / "apps" / "workspace"


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


# The plugin tiles the Home layout is specified against. registry.py appends
# these manifests only when the backing package is importable (no dead tiles on
# a host without it), and CI installs `.[all,dev]`, which ships scitex-cards but
# not scitex-storage or scitex-agent-container. These tests pin the LAYOUT, so
# they register the manifests themselves instead of inheriting the environment.
_PLUGIN_TILE_MANIFESTS = (
    "workspace/todo_app/manifest.json",
    "workspace/storage_app/manifest.json",
    "workspace/agents_app/manifest.json",
)


def _register_plugin_tiles() -> list[str]:
    """Register any plugin tile the environment left out; return what was added."""
    added = []
    for rel_path in _PLUGIN_TILE_MANIFESTS:
        config = registry._manifest_to_module_config(
            registry._load_manifest(registry._APPS_ROOT / rel_path)
        )
        if registry.get_module(config.name) is None:
            registry.register_module(config)
            added.append(config.name)
    return added


def _unregister(names: list[str]) -> None:
    for name in names:
        registry.unregister_module(name)


# SCITEX_HUB_INTERNAL_APPS_RELEASED=True: Agents and Cards (visibility
# internal) are on the grid, as on the dev deployment.
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
class HomePagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(_unregister, _register_plugin_tiles())

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="home-pages-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)
        # These tests pin the layout of a grid holding every app, so only Home stays docked.
        self.client.get("/apps/")
        self.client.post(
            "/apps/store/api/dock/",
            data=json.dumps({"dock": ["launcher"]}),
            content_type="application/json",
        )

    def test_home_renders_page_dots_with_desktop_arrows(self):
        # Arrange
        url = "/apps/"
        # Act
        content = self.client.get(url).content
        # Assert
        assert b'id="launcher-dots"' in content and b'id="launcher-page-next"' in content

    def _groups(self):
        return self.client.get("/apps/").context["groups"]

    def test_groups_come_in_the_operator_order(self):
        # Operator 2026-09-14: Foundation, Work, Publish, System, never interleaved.
        # Arrange
        groups = self._groups()
        # Act
        keys = [group["key"] for group in groups]
        # Assert
        assert keys == ["foundation", "work", "publish", "system"]

    def test_foundation_group_holds_the_infrastructure_apps_and_storage(self):
        # Arrange
        groups = self._groups()
        # Act
        names = [c.get("name") for c in groups[0]["cells"] if not c.get("is_planned")]
        # Assert
        assert names == ["home", "agents", "todo", "storage", "files"]

    def test_files_placeholder_is_gone_once_the_files_app_exists(self):
        # Arrange
        groups = self._groups()
        # Act
        names = [c.get("name") for g in groups for c in g["cells"] if c.get("is_planned")]
        # Assert
        assert "files" not in names

    def test_first_row_is_exactly_the_four_infrastructure_apps(self):
        # Rows of 4 at every width: the first band's first row.
        # Arrange
        groups = self._groups()
        # Act
        first_row = [cell.get("name") for cell in groups[0]["cells"][:4]]
        # Assert
        assert first_row == ["home", "agents", "todo", "storage"]

    def test_missing_stats_app_is_a_coming_soon_tile_not_an_empty_cell(self):
        # Walkthrough 2026-09-14: the held Stats gap read as a broken grid.
        # Arrange
        groups = self._groups()
        # Act
        cells = [
            (c.get("name"), bool(c.get("is_planned")))
            for c in groups[1]["cells"]
            if not c.get("is_planned") or c.get("name") == "stats"
        ]
        # Assert
        assert cells == [
            ("scholar", False),
            ("figrecipe", False),
            ("stats", True),
            ("writer", False),
            ("chat", False),
            ("tools-image", False),
            ("tools-pdf", False),
            ("tools-text", False),
            ("tools-developer", False),
            ("tools-media", False),
            ("create-app", False),
        ]

    def test_home_renders_no_empty_slot_cell(self):
        # Arrange
        url = "/apps/"
        # Act
        content = self.client.get(url).content
        # Assert
        assert b'class="launcher-slot"' not in content

    def test_publish_group_holds_slides_and_public_projects(self):
        # Proposed 2026-09-14 (Telegram 6040): showing work outside.
        # Arrange
        groups = self._groups()
        # Act
        names = [c.get("name") for c in groups[2]["cells"] if not c.get("is_planned")]
        # Assert
        assert names == ["slides", "discovery"]

    def test_publish_group_holds_the_live_paper_and_agentic_journal_placeholders(self):
        # Arrange
        groups = self._groups()
        # Act
        planned = [c.get("name") for c in groups[2]["cells"] if c.get("is_planned")]
        # Assert
        assert planned == ["live-paper", "agentic-journal"]

    def test_slides_placeholder_is_gone_once_the_slides_app_exists(self):
        # Arrange
        groups = self._groups()
        # Act
        names = [c.get("name") for g in groups for c in g["cells"] if c.get("is_planned")]
        # Assert
        assert "slides" not in names

    def test_system_group_holds_settings_docs_and_app_store(self):
        # Arrange
        groups = self._groups()
        # Act
        names = [cell.get("name") for cell in groups[3]["cells"]]
        # Assert
        assert names == ["settings", "docs", "store"]

    def test_each_group_is_an_aria_group_with_a_translatable_label(self):
        # Arrange
        content = self.client.get("/apps/").content.decode("utf-8")
        # Act
        bands = re.findall(
            r'<div class="launcher-group" role="group" data-group="(\w+)" aria-label="([^"]+)"',
            content,
        )
        # Assert
        assert bands == [
            ("foundation", "Foundation"),
            ("work", "Work"),
            ("publish", "Publish"),
            ("system", "System"),
        ]

    def test_every_tile_carries_its_group(self):
        # Arrange
        content = self.client.get("/apps/").content.decode("utf-8")
        # Act
        pairs = dict(re.findall(r'data-module="([^"]+)"\s+data-group="(\w+)"', content))
        # Assert
        assert (pairs.get("storage"), pairs.get("chat"), pairs.get("store")) == (
            "foundation",
            "work",
            "system",
        )

    def test_group_tints_exist_for_both_themes(self):
        # Arrange
        css = _launcher_css("grid.css")
        # Act
        light = re.findall(r'^\.launcher-group\[data-group="(\w+)"\]\s*\{\s*--launcher-band', css, re.M)
        dark = re.findall(r'^\[data-theme="dark"\] \.launcher-group\[data-group="(\w+)"\]\s*\{\s*--launcher-band', css, re.M)
        # Assert
        assert (sorted(light), sorted(dark)) == (
            ["foundation", "publish", "system", "work"],
            ["foundation", "publish", "system", "work"],
        )

    def test_grid_is_four_columns_at_every_width(self):
        # Arrange
        css = _launcher_css("grid.css") + _launcher_css("mobile.css")
        # Act
        declared = set(re.findall(r"--launcher-cols:\s*(\d+)", css))
        # Assert
        assert declared == {"4"}

    def test_paged_grid_lays_pages_out_in_a_row(self):
        # Operator iPhone 2026-09-14: swiping did not turn the page. The paged
        # grid inherited flex-direction: column from .launcher-grid, so the
        # pages stacked vertically and the scroller had nothing to scroll
        # sideways (scrollWidth == clientWidth in WebKit and Chromium).
        # Arrange
        css = _launcher_css("mobile.css")
        # Act
        rule = re.search(r"\.launcher-grid--paged\s*\{([^}]*)\}", css).group(1)
        # Assert
        assert re.search(r"flex-direction:\s*row", rule)

    def test_group_label_is_the_bands_aria_label(self):
        # Arrange
        css = _launcher_css("grid.css")
        # Act
        rule = re.search(r"\.launcher-group\[aria-label\]::before\s*\{([^}]*)\}", css)
        # Assert
        assert rule and "attr(aria-label)" in rule.group(1)

    def test_group_label_never_takes_a_grid_cell(self):
        # Arrange — a grid container's pseudo-element is a grid item unless
        # it is taken out of flow.
        css = _launcher_css("grid.css")
        # Act
        rule = re.search(r"\.launcher-group\[aria-label\]::before\s*\{([^}]*)\}", css).group(1)
        # Assert
        assert re.search(r"position:\s*absolute", rule)

    def test_group_band_carries_its_translated_label(self):
        # Arrange
        content = self.client.get("/apps/").content.decode("utf-8")
        # Act
        labels = re.findall(r'class="launcher-group" role="group" data-group="(\w+)" aria-label="([^"]+)"', content)
        # Assert
        assert dict(labels) == {"foundation": "Foundation", "work": "Work", "publish": "Publish", "system": "System"}

    def test_page_arrows_render_hidden(self):
        # Arrange
        content = self.client.get("/apps/").content.decode("utf-8")
        # Act
        arrow = re.search(r'<button[^>]*id="launcher-page-next"[^>]*>', content).group(0)
        # Assert
        assert re.search(r"\shidden(\s|>|$)", arrow)

    def test_page_arrows_only_show_on_wide_fine_pointer_viewports(self):
        # Operator iPhone 2026-09-14: arrows showed as white boxes above the
        # grid and beside the dock. They may only appear inside this media query.
        # Arrange
        css = _launcher_css("mobile.css")
        # Act
        shown = re.findall(
            r"@media([^{]*)\{\s*\.launcher-page-arrow:not\(\[hidden\]\)\s*\{[^}]*display:\s*inline-flex",
            css,
        )
        # Assert
        assert shown == [" (min-width: 768px) and (hover: hover) and (pointer: fine) "]

    def test_reorder_travel_is_between_300_and_350ms(self):
        # Operator 2026-09-14: displaced icons jumped too fast when swapping.
        # Arrange
        css = _launcher_css("edit-mode.css")
        # Act
        base = re.search(r"\.launcher-grid\s*\{[^}]*--launcher-travel-ms:\s*(\d+)", css)
        # Assert
        assert base is not None and 300 <= int(base.group(1)) <= 350

    def test_reduced_motion_stops_the_wiggle_and_makes_moves_instant(self):
        # Arrange
        css = _launcher_css("edit-mode.css")
        # Act
        block = re.search(
            r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*)\}\s*$", css, re.DOTALL
        ).group(1)
        # Assert
        assert re.search(r"--launcher-travel-ms:\s*0", block) and re.search(
            r"animation:\s*none", block
        )

    def test_home_body_is_the_scrolling_app_home(self):
        # Arrange — app-home releases the viewport lock so the footer can scroll
        # into view above the dock.
        url = "/apps/"
        # Act
        body = re.search(rb"<body[^>]*>", self.client.get(url).content).group(0)
        # Assert
        assert b"app-home" in body


class TileBadgeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="badge-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        AppsModule.objects.create(
            module_name="scitex-badge-probe-app",
            label="Badge Probe",
            category="other",
            visibility="public",
            availability="desktop_only",
            status="wip",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _tile_html(self, name: str) -> str:
        text = self.client.get("/apps/").content.decode("utf-8")
        start = text.index(f'data-module="{name}"')
        return text[start : text.index("</a>", start)]

    def test_badges_sit_inside_the_tile_icon(self):
        # Arrange
        parser = _AncestorClasses("launcher-badge")
        # Act
        parser.feed(self.client.get("/apps/").content.decode("utf-8"))
        # Assert — every badge has the icon box AND the tile as ancestors
        assert parser.found and all(
            any("launcher-tile-icon" in c.split() for c in chain)
            and any("launcher-tile" in c.split() for c in chain)
            for chain in parser.found
        )

    def test_badge_css_has_no_outward_offset(self):
        # Arrange
        css = (
            _WORKSPACE / "apps_app/static/apps_app/css/launcher/grid.css"
        ).read_text("utf-8")
        # Act
        badge_rules = re.findall(r"\.launcher-badge[^{]*\{[^}]*\}", css)
        # Assert — the old pills were pushed out with translateX(46px)
        assert badge_rules and not any("translate" in rule for rule in badge_rules)

    def test_desktop_only_and_dev_only_stack_in_one_slot(self):
        # Arrange
        tile = self._tile_html("scitex-badge-probe-app")
        # Act
        slot = tile[tile.index('class="launcher-tile-badges"') :]
        kinds = re.findall(r"launcher-badge-(desktop-only|dev-only)", slot)
        # Assert
        assert tile.count('class="launcher-tile-badges"') == 1 and kinds == [
            "desktop-only",
            "dev-only",
        ]

    def test_status_badge_is_at_most_a_third_of_the_icon(self):
        # Operator iPhone 2026-09-14: the monitor badge covered ~45% of the tile.
        # Arrange
        css = _launcher_css("grid.css")
        # Act
        ratio = _icon_ratio(css, r"\.launcher-tile-icon \.launcher-badge")
        # Assert
        assert ratio is not None and ratio <= 0.32

    def test_globe_badge_is_a_corner_badge_not_a_second_icon(self):
        # Operator iPhone 2026-09-14: the globe rendered full-size beside the folder.
        # Arrange
        css = _launcher_css("grid.css")
        # Act
        ratio = _icon_ratio(css, r"\.launcher-tile-icon-badge")
        # Assert
        assert ratio is not None and 0.30 <= ratio <= 0.40

    def test_desktop_only_tiles_are_explicitly_not_dimmed_on_a_phone(self):
        # Arrange
        css = _launcher_css("mobile.css")
        # Act
        undimmed = re.search(
            r'data-availability="desktop_only"\]\s*\.launcher-tile-icon[^{]*\{[^}]*opacity:\s*1;[^}]*filter:\s*none',
            css,
        )
        # Assert
        assert undimmed is not None

    def test_launcher_stylesheets_are_cache_busted(self):
        # A stale @import-ed grid/mobile.css is what the operator's phone showed.
        # Arrange
        url = "/apps/"
        # Act
        links = re.findall(
            rb'href="[^"]*apps_app/css/launcher/(?:core|grid|mobile|edit-mode)\.css\?v=[^"]*"',
            self.client.get(url).content,
        )
        # Assert
        assert len(links) == 4

    def test_desktop_only_badge_says_mobile_layout_coming_soon(self):
        # Arrange
        tile = self._tile_html("scitex-badge-probe-app")
        # Act
        badge = re.search(r'launcher-badge-desktop-only"[^>]*aria-label="([^"]+)"', tile)
        # Assert
        assert badge.group(1) == "Mobile layout coming soon"



# EOF
