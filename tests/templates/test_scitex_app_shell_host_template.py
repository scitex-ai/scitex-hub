"""The hub provides the host shell that mounted leaf apps extend.

scitex-agent-container's dashboard templates start with
``{% extends "scitex_app/app_shell.html" %}``. The hub is the host, so the hub
must ship that template; when it did not, /apps/agents/ returned 500 for staff
on the dev server (2026-09-14) while anonymous and non-operator requests looked
healthy (302 / 403), because neither of those reaches a template.
"""

from django.template import Context, Template


def test_leaf_content_block_renders_inside_the_host_shell():
    # Arrange
    leaf = Template(
        '{% extends "scitex_app/app_shell.html" %}'
        "{% block scitex_app_content %}LEAF-MARKER-7f3a{% endblock %}"
    )

    # Act
    html = leaf.render(Context({}))

    # Assert
    assert "LEAF-MARKER-7f3a" in html
