"""The header search icon is a CSS mask painted with the header text token."""

from pathlib import Path

SEARCH = Path(__file__).resolve().parents[2] / "templates/global_base_partials/global_header/search.html"


def test_search_icons_are_not_images():
    # Arrange: an <img> paints the SVG's currentColor black, invisible on the dark header.
    template = SEARCH.read_text(encoding="utf-8")
    # Act
    images = template.count("<img")
    # Assert
    assert images == 0
