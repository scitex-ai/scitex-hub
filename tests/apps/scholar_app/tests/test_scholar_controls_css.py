"""The page /apps/scholar/ renders must link the shared Scholar control sheet."""

from pathlib import Path

APP = Path(__file__).resolve().parents[4] / "apps" / "workspace" / "scholar_app"


def test_unified_template_links_the_controls_sheet():
    # Arrange: the phone toolbar/tab fixes live only in this sheet.
    path = APP / "templates/scholar_app/scholar_unified.html"
    # Act
    template = path.read_text()
    # Assert
    assert "scholar_app/css/common/08-scholar-controls.css" in template


def test_library_collection_filter_is_a_select():
    # Arrange: the old round "All" pill was replaced by a collection dropdown.
    path = APP / "templates/scholar_app/library_partials/library_main.html"
    # Act
    template = path.read_text()
    # Assert
    assert '<select class="library-filter-select"\n                id="library-collection-select"' in template
