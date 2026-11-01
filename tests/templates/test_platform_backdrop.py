"""Host-owned backdrop reaches both native and mounted shells without a fork."""

import re
from hashlib import sha256
from pathlib import Path

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.workspace_app.middleware_site_content_frame import (
    FRAME_STYLESHEET,
    LEAF_CHROME_STYLESHEET,
    PLATFORM_BACKDROP_STYLESHEET,
    inject_frame_stylesheet,
)

ROOT = Path(__file__).resolve().parents[2]
LAYOUTS = ROOT / "static/shared/css/layouts"


def test_both_real_paths_load_the_same_independently_versioned_backdrop():
    # Arrange
    native = (LAYOUTS / "global-base.css").read_text()
    leaf = (LAYOUTS / "leaf-host-chrome.css").read_text()
    middleware = (
        ROOT / "apps/infra/workspace_app/middleware_site_content_frame.py"
    ).read_text()
    # Act
    native_imports = re.findall(r'@import\s+url\("([^\"]+)"\)', native)
    # Assert
    assert (
        native_imports.count("platform-backdrop.css") == 1
        and "platform-backdrop.css" not in leaf
        and "versioned_static(PLATFORM_BACKDROP_STYLESHEET)" in middleware
    )


def test_theme_gradients_have_one_host_owned_source():
    # Arrange
    source = (LAYOUTS / "platform-backdrop.css").read_text()
    others = [
        (LAYOUTS / name).read_text()
        for name in ("global-base.css", "leaf-host-chrome.css")
    ]
    # Act
    theme_rules = re.findall(
        r'(?:\[data-theme="dark"\] )?body::before\s*\{([^}]+)\}', source
    )
    # Assert
    assert (
        len(theme_rules) == 2
        and all("radial-gradient(" in rule for rule in theme_rules)
        and all("body::before" not in text for text in others)
    )


def test_platform_ground_does_not_add_global_body_rules_or_intercept_input():
    # Arrange
    css = (LAYOUTS / "platform-backdrop.css").read_text()
    # Act
    root_rules = re.findall(r"(?:^|})\s*body\s*\{", css)
    # Assert
    assert (
        not root_rules
        and "pointer-events: none;" in css
        and "body > .workspace-three-col" in css
        and "z-index: 1;" in css
    )


def test_existing_desktop_frame_contract_is_preserved():
    # Arrange
    css = (LAYOUTS / "site-content-frame.css").read_text()
    # Act
    frame = re.search(r"--site-content-max-width:\s*min\(90vw,\s*2560px\)", css)
    # Assert
    assert (
        frame
        and "--app-accent-color" not in css
        and "body > .workspace-three-col" in css
    )


def test_injected_host_stylesheets_use_their_actual_content_hashes():
    # Arrange
    request = RequestFactory().get("/apps/example/")
    request.user = AnonymousUser()
    response = HttpResponse(
        '<html><head></head><body><header class="global-header"></header><div id="workspace-three-col"></div></body></html>'
    )
    # Act
    inject_frame_stylesheet(request, response)
    html = response.content.decode()
    expected = [
        f"/static/{path}?v={sha256((ROOT / 'static' / path).read_bytes()).hexdigest()[:12]}"
        for path in (
            FRAME_STYLESHEET,
            LEAF_CHROME_STYLESHEET,
            PLATFORM_BACKDROP_STYLESHEET,
        )
    ]
    # Assert
    assert all(url in html for url in expected)
