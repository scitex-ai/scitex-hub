"""Tools is split into category tiles, each at /apps/tools/<category>/."""

from __future__ import annotations

from django.test import TestCase

from apps.infra.workspace_app.registry import extract_module_from_path, get_module
from apps.workspace.tools_app.views.tools_data import TOOL_CATEGORIES

CATEGORIES = ("image", "pdf", "text", "developer", "media")


def test_every_category_has_a_registered_tile():
    # Arrange
    names = [f"tools-{slug}" for slug in CATEGORIES]
    # Act
    modules = [get_module(name) for name in names]
    # Assert
    assert all(m is not None and m.show_in_launcher for m in modules)


def test_tile_list_matches_the_category_data():
    # Arrange
    expected = set(CATEGORIES)
    # Act
    actual = set(TOOL_CATEGORIES)
    # Assert
    assert actual == expected


def test_category_url_maps_to_its_tile_and_tool_routes_stay_tools():
    # Arrange
    paths = ("/apps/tools/pdf/", "/apps/tools/merge-pdf/")
    # Act
    found = [extract_module_from_path(p) for p in paths]
    # Assert
    assert found == ["tools-pdf", "tools"]


def test_old_tools_tile_is_hidden_but_registered():
    # Arrange
    mod = get_module("tools")
    # Act
    hidden = not mod.show_in_launcher
    # Assert
    assert hidden


class ToolsCategoryPageTest(TestCase):
    def test_category_page_lists_only_its_domains(self):
        # Arrange
        url = "/apps/tools/text/"
        # Act
        response = self.client.get(url)
        # Assert
        assert [d["slug"] for d in response.context["domains"]] == ["text", "research"]

    def test_category_page_uses_its_own_panes_app_id(self):
        # Arrange
        url = "/apps/tools/text/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-stx-panes="tools-text"' in response.content

    def test_unknown_category_is_404_and_all_tools_still_render(self):
        # Arrange
        urls = ("/apps/tools/nope/", "/apps/tools/")
        # Act
        codes = [self.client.get(u).status_code for u in urls]
        # Assert
        assert codes == [404, 200]
