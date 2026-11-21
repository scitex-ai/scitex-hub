"""Current-page Markdown must export the selected, contained Sphinx document."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.docs_app import _sphinx, views


@pytest.fixture
def package_docs(tmp_path, monkeypatch):
    base = tmp_path / "docs"
    base.mkdir()
    (base / "index.html").write_text(
        '<div role="main"><h1>Package index</h1><p>INDEX CONTENT</p></div>'
    )
    (base / "cli.html").write_text(
        '<div role="main"><h1>CLI reference</h1><p>CLI DETAILS</p></div>'
    )
    secret = tmp_path / "secret.html"
    secret.write_text('<div role="main">PRIVATE SENTINEL</div>')
    (base / "leak.html").symlink_to(secret)
    monkeypatch.setattr(_sphinx, "resolve_sphinx_path", lambda _: base)
    monkeypatch.setattr(_sphinx, "list_sphinx_pages", lambda _: [])
    monkeypatch.setitem(
        views._PAGES_BY_SLUG,
        "pkg-fixture",
        {
            "slug": "pkg-fixture",
            "label": "Fixture",
            "template": "docs_app/docs_sphinx_package.html",
        },
    )
    return base


@pytest.mark.parametrize(
    "query,expected,absent",
    [
        ("?page=cli.html", "CLI DETAILS", "INDEX CONTENT"),
        ("", "INDEX CONTENT", "CLI DETAILS"),
        ("?page=../secret.html", "INDEX CONTENT", "PRIVATE SENTINEL"),
        ("?page=leak.html", "INDEX CONTENT", "PRIVATE SENTINEL"),
    ],
)
def test_markdown_export_respects_subpage_and_existing_containment(
    package_docs, query, expected, absent
):
    request = RequestFactory().get("/apps/docs/export/pkg-fixture/" + query)
    request.user = AnonymousUser()
    response = views.docs_export(request, "pkg-fixture")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/markdown")
    assert "attachment;" in response["Content-Disposition"]
    content = response.content.decode()
    assert expected in content
    assert absent not in content
