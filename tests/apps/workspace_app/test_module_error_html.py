"""Unknown-module responses display supplied labels as inert text."""

from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.infra.workspace_app.views import (
    _render_dev_template,
    workspace_module_content,
)


class _ResponseMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_data(self, data):
        self.text.append(data)


@pytest.mark.parametrize("prefix", ["unknown-", "dev__"])
@pytest.mark.parametrize("payload", ['<img src=x onerror="alert(1)">', "missing-module"])
def test_unknown_module_label_is_text_not_executable_html(prefix, payload):
    # Arrange: an authenticated component request; no ORM or container call.
    request = RequestFactory().get("/workspace/module/", HTTP_X_WORKSPACE_SHELL="1")
    request.user = SimpleNamespace(is_authenticated=True)

    # Act: exercise both actual missing-module routes, then parse their HTML.
    response = workspace_module_content(request, prefix + payload)
    markup = _ResponseMarkup()
    markup.feed(response.content.decode())

    # Assert: the whole label is visible, without introducing an HTML element.
    assert (response.status_code, markup.tags, payload in "".join(markup.text)) == (
        404,
        [],
        True,
    )


def test_render_failure_does_not_disclose_template_diagnostics(tmp_path):
    # Arrange: a real malformed template whose parser error contains a marker.
    marker = "private_template_diagnostic_fixture"
    path = tmp_path / "private-template.html"
    path.write_text("{% " + marker + " %}")
    request = RequestFactory().get("/workspace/module/")

    # Act: exercise the same renderer used after the ownership gate.
    response = _render_dev_template(path, {}, request, "dev__owner__app")

    # Assert: callers get a useful refusal without the parser's raw details.
    assert (response.status_code, response.content.decode()) == (
        500,
        "Dev module 'dev__owner__app' could not be rendered",
    )


def test_render_failure_label_cannot_introduce_html(tmp_path):
    # Arrange: real template parsing fails, with a markup-shaped module label.
    path = tmp_path / "bad.html"
    path.write_text("{% unknown_fixture_tag %}")
    payload = '<img src=x onerror="alert(1)">'
    request = RequestFactory().get("/workspace/module/")

    # Act: parse the actual render-error response as HTML.
    response = _render_dev_template(path, {}, request, payload)
    markup = _ResponseMarkup()
    markup.feed(response.content.decode())

    # Assert: the label survives as inert text, without an image element.
    assert (response.status_code, markup.tags, payload in "".join(markup.text)) == (
        500,
        [],
        True,
    )


def test_template_renderer_keeps_html_and_escapes_context(tmp_path):
    # Arrange: real app HTML; omit unrelated request/database context processors.
    path = tmp_path / "good.html"
    path.write_text("<p>{{ value }}</p>")
    payload = '<img src=x onerror="alert(1)">'

    # Act: render through the unchanged Django template engine.
    response = _render_dev_template(path, {"value": payload}, None, "dev__owner__app")
    markup = _ResponseMarkup()
    markup.feed(response.content.decode())

    # Assert: legitimate HTML remains, and user data is still just text.
    assert (response.status_code, markup.tags, "".join(markup.text)) == (
        200,
        ["p"],
        payload,
    )
