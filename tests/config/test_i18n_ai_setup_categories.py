"""AI Setup section names follow the active language (English default, full Japanese).

Before this change the category names and section titles were bare English
string literals in apps/infra/accounts_app/views/ai_setup.py, so the AI Setup
page stayed English under Japanese.
"""

from django.utils import translation

from apps.infra.accounts_app.views.ai_setup import _SECTIONS, _get_categories


def test_category_names_are_japanese_under_ja():
    # Arrange
    translation.activate("ja")

    # Act
    names = [c["name"] for c in _get_categories()]
    translation.deactivate()

    # Assert
    assert names == ["スキル", "コマンド", "フック", "MCP サーバー", "CLI コマンド", "AI プロバイダー"]


def test_category_names_stay_english_under_en():
    # Arrange
    translation.activate("en")

    # Act
    names = [c["name"] for c in _get_categories()]
    translation.deactivate()

    # Assert
    assert names == ["Skills", "Commands", "Hooks", "MCP Servers", "CLI Commands", "AI Providers"]


def test_category_descriptions_contain_no_english_sentence_under_ja():
    # Arrange
    translation.activate("ja")

    # Act
    descriptions = [c["description"] for c in _get_categories()]
    translation.deactivate()

    # Assert
    assert "Automated actions triggered by events" not in descriptions


def test_section_title_is_japanese_under_ja():
    # Arrange
    translation.activate("ja")

    # Act
    title = str(_SECTIONS["hooks"]["title"])
    translation.deactivate()

    # Assert
    assert title == "フック"


def test_section_title_stays_english_under_en():
    # Arrange
    translation.activate("en")

    # Act
    title = str(_SECTIONS["mcp-servers"]["title"])
    translation.deactivate()

    # Assert
    assert title == "MCP Servers"
