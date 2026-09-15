"""Source contracts for the shared responsive header and launcher template."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

ROOT = Path(settings.BASE_DIR)
HEADER = ROOT / "templates/global_base_partials/global_header.html"
HEADER_CSS = ROOT / "static/shared/css/components/header/14-responsive.css"
LAUNCHER = ROOT / "apps/workspace/apps_app/templates/apps_app/launcher.html"
LAUNCHER_GRID_CSS = (
    ROOT / "apps/workspace/apps_app/static/apps_app/css/launcher/grid.css"
)
LAUNCHER_RESPONSIVE_CSS = (
    ROOT / "apps/workspace/apps_app/static/apps_app/css/launcher/mobile.css"
)


def _rule(css: str, selector: str) -> str:
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", stripped)
    assert match, f"missing {selector!r} in stylesheet"
    return re.sub(r"\s+", " ", match.group(1))


def test_one_hamburger_is_the_last_header_row_control_at_every_width():
    template = HEADER.read_text(encoding="utf-8")
    header_row = template.split('<div class="global-header-inner">', 1)[1].split(
        "</div>\n    </div>", 1
    )[0]

    assert header_row.count('id="mobile-hamburger-btn"') == 1
    assert 'class="header-right"' not in header_row
    assert header_row.rfind('id="mobile-hamburger-btn"') > header_row.rfind(
        'class="header-search-mobile-trigger"'
    )


def test_theme_help_and_account_actions_live_inside_the_shared_menu():
    template = HEADER.read_text(encoding="utf-8")
    menu = template.split('id="mobile-header-menu"', 1)[1].split("</header>", 1)[0]
    before_menu = template.split('id="mobile-header-menu"', 1)[0]

    assert 'id="theme-toggle"' in menu
    assert 'id="product-tour-btn"' in menu
    assert 'href="/accounts/profile/"' in menu
    assert 'href="/accounts/settings/"' in menu
    assert 'id="theme-toggle"' not in before_menu
    assert 'id="product-tour-btn"' not in before_menu
    assert 'id="user-menu-toggle"' not in template


def test_shared_hamburger_keeps_a_44px_target_outside_mobile_media_query():
    css = HEADER_CSS.read_text(encoding="utf-8")
    base = _rule(css, ".mobile-hamburger")

    assert "display: flex" in base
    assert re.search(r"width\s*:\s*44px", base)
    assert re.search(r"height\s*:\s*44px", base)
    assert css.index(".mobile-hamburger {") < css.index("@media (max-width: 768px)")


def test_launcher_uses_one_group_and_tile_hierarchy_for_all_viewports():
    template = LAUNCHER.read_text(encoding="utf-8")

    assert template.count('class="launcher-grid"') == 1
    assert template.count('class="launcher-group"') >= 1
    assert "launcher-mobile" not in template
    assert "launcher-desktop" not in template


def test_responsive_launcher_changes_variables_not_panel_or_tile_shape():
    grid_css = LAUNCHER_GRID_CSS.read_text(encoding="utf-8")
    responsive_css = LAUNCHER_RESPONSIVE_CSS.read_text(encoding="utf-8")

    assert "--launcher-panel-radius" in _rule(grid_css, ".launcher-grid")
    assert "border-radius: var(--launcher-panel-radius)" in _rule(
        grid_css, ".launcher-group"
    )
    assert "border-radius: var(--launcher-tile-radius)" in _rule(
        grid_css, ".launcher-tile"
    )
    assert not re.search(
        r"@media\s*\(max-width:[^{]+\{.*?\.launcher-group\s*\{[^}]*border-radius",
        responsive_css,
        flags=re.DOTALL,
    )
    assert not re.search(
        r"@media\s*\(max-width:[^{]+\{.*?\.launcher-tile\s*\{[^}]*border-radius",
        responsive_css,
        flags=re.DOTALL,
    )
