"""The old template's lone 」 after %%%% EOF is removed, nothing else is touched."""

from apps.workspace.writer_app.services.template_stray_bracket import (
    strip_stray_bracket_text,
)


def test_lone_bracket_after_eof_is_removed_and_body_brackets_kept():
    # Arrange
    text = "\\begin{abstract}\n「引用」\n\\end{abstract}\n\n%%%% EOF\n」"
    # Act
    fixed = strip_stray_bracket_text(text)
    # Assert
    assert fixed == "\\begin{abstract}\n「引用」\n\\end{abstract}\n\n%%%% EOF\n"
