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
