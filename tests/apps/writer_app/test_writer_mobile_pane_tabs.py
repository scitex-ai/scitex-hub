"""Both Writer workspace templates must mount the phone pane tabs.

index.html and writer_partial.html each carry a copy of .writer-workspace;
patching only one is how the 2026-08-04 phone regression shipped.
"""

from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[3] / "apps/workspace/writer_app/templates/writer_app"
INCLUDE = '{% include "writer_app/index_partials/mobile_pane_tabs.html" %}'


def test_every_writer_workspace_template_includes_the_phone_tabs():
    # Arrange
    names = ("index.html", "writer_partial.html")
    # Act
    missing = [n for n in names if INCLUDE not in (TEMPLATES / n).read_text(encoding="utf-8")]
    # Assert
    assert missing == []
