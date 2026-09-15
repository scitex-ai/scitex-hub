#!/usr/bin/env python3
"""Desktop pages sit in a centred frame sized by --site-content-max-width.

Operator 2026-09-14: on large displays content should use about 90% of the
viewport, with whitespace margins left and right. The rendered widths are
checked in tests/e2e/playwright/test_desktop_content_frame_is_90vw.py; this
file pins the CSS, the template link, and the leaf-page stylesheet injection.

No mocks. One assertion per test.
"""

import re
from pathlib import Path

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.workspace_app.middleware_site_content_frame import (
    FRAME_STYLESHEET,
    inject_frame_stylesheet,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRAME_CSS = PROJECT_ROOT / "static" / FRAME_STYLESHEET
HEAD_STYLES = PROJECT_ROOT / "templates" / "global_base_partials" / "global_head_styles.html"
STANDALONE_PAGE = (
    '<html><head><title>Leaf</title></head>'
    '<body><div id="workspace-three-col"></div></body></html>'
)


def _desktop_rule_for(selector: str) -> str:
    css = FRAME_CSS.read_text()
    desktop_block = css.split("@media (min-width: 1024px)", 1)[1].split("{", 1)[1]
    for selector_list, body in re.findall(r"([^{}]*)\{([^}]*)\}", desktop_block):
        if selector in [part.strip() for part in selector_list.split(",")]:
            return body
    return ""


def _inject(html: str) -> str:
    request = RequestFactory().get("/apps/scholar/v2/")
    request.user = AnonymousUser()
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    inject_frame_stylesheet(request, response)
    return response.content.decode()


def test_frame_css_defines_the_site_content_max_width_token():
    # Arrange
    css = FRAME_CSS.read_text()

    # Act
    declaration = re.search(r"--site-content-max-width:\s*min\(90vw,\s*2560px\);", css)

    # Assert
    assert declaration is not None


def test_main_content_wrapper_uses_the_token_on_desktop():
    # Arrange
    selector = "body > #main-content"

    # Act
    rule = _desktop_rule_for(selector)

    # Assert
    assert "width: var(--site-content-max-width);" in rule


def test_workspace_layout_uses_the_token_on_desktop():
    # Arrange
    selector = "body > .workspace-layout"

    # Act
    rule = _desktop_rule_for(selector)

    # Assert
    assert "width: var(--site-content-max-width);" in rule


def test_global_head_styles_link_the_frame_css():
    # Arrange
    template = HEAD_STYLES.read_text()

    # Act
    linked = f"{{% static '{FRAME_STYLESHEET}' %}}" in template

    # Assert
    assert linked


def test_standalone_leaf_page_gets_the_frame_stylesheet():
    # Arrange
    html = STANDALONE_PAGE

    # Act
    rendered = _inject(html)

    # Assert
    assert FRAME_STYLESHEET in rendered.split("</head>", 1)[0]


def test_standalone_leaf_page_gets_the_hub_site_header():
    # Arrange
    html = STANDALONE_PAGE

    # Act
    rendered = _inject(html)

    # Assert
    assert "data-leaf-site-header" in rendered.split('id="workspace-three-col"', 1)[0]


def test_site_header_skips_a_body_tag_inside_a_comment():
    # Arrange
    html = STANDALONE_PAGE.replace("</head>", "</head><!-- mirrors onto <body> -->")

    # Act
    rendered = _inject(html)

    # Assert
    assert "data-leaf-site-header" in rendered.split("-->", 1)[1]


def test_leaf_page_with_its_own_app_header_gets_no_second_header():
    # Arrange
    html = STANDALONE_PAGE.replace("<body>", '<body><header class="app-header"></header>')

    # Act
    rendered = _inject(html)

    # Assert
    assert "data-leaf-site-header" not in rendered


def test_standalone_leaf_tab_icon_is_the_hub_favicon():
    # Arrange
    from django.templatetags.static import static

    from config.context_processors import scitex_env

    default_href = static("scitex_ui/img/scitex-favicon.svg")
    html = STANDALONE_PAGE.replace("</head>", f'<link rel="icon" href="{default_href}" /></head>')
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    hub_href = static(scitex_env(request)["SCITEX_FAVICON"])

    # Act
    rendered = _inject(html)

    # Assert
    assert f'rel="icon" href="{hub_href}"' in rendered


def test_page_without_the_standalone_shell_is_left_unchanged():
    # Arrange
    html = "<html><head></head><body><main id=\"main-content\"></main></body></html>"

    # Act
    rendered = _inject(html)

    # Assert
    assert rendered == html
