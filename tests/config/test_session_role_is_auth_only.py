"""The shell's session role is derived directly from authentication."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GLOBAL_BASE = REPO / "templates/global_base.html"


def test_global_base_derives_session_role_from_authentication_only():
    template = GLOBAL_BASE.read_text()

    assert (
        'data-session-role="{% if user.is_authenticated %}user'
        '{% else %}anonymous{% endif %}"'
    ) in template
    assert "session_role|default" not in template
