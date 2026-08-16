#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar must lead with Search — in the template the URL ACTUALLY RESOLVES TO.

WHAT WENT WRONG. The operator asked twice, in plain language, that Scholar's
tab bar lead with Search rather than Library:

    2026-08-16 10:12  「ライブラリが1番左ではなくて、先にサーチがあったほうがいいと思います」
    2026-08-16 11:17  「scholar　はサーチが左側でお願いします。」(with a screenshot)

PR #616 reordered ``scholar_app/scholar_partial.html``, went green on 19 CI
checks, deployed, and was reported to the operator as done. It changed the
WRONG FILE. ``/apps/scholar/`` is rendered from ``scholar_unified.html``, which
#616 never touched, so the live page kept opening with Library leftmost and
Library active. Measured on production the next day:

    nav.scholar-tabs -> ["library", "search", "bibtex", "graph"]   (activeTab: library)

Neither the green CI run nor the successful deploy was EVIDENCE ABOUT THE PAGE
THE USER LOOKS AT, because no test asserted the tab order of any template, let
alone of the one the URL resolves to.

WHY THIS TEST IS DERIVED, NOT HARDCODED. A test that opened
``scholar_unified.html`` by path would have been just as green while #616 edited
its neighbour, and would rot the moment the view starts rendering something
else. So this file starts at the URL, resolves it through the real URLconf to
the real view, reads the template name OUT OF THAT VIEW, and asks Django's own
loader where that template lives on disk. Editing the wrong file therefore
cannot pass: the test follows the route, not a filename.

The tab bar is declared in more than one template (they are separate live
surfaces of the same app: the standalone page and the workspace SPA module
pane), and the order is ALSO hardcoded in TypeScript, which decides which tab
opens. Duplication is why this survived a green PR, so all copies are swept
here rather than only the one that broke.
"""

import ast
import inspect
import re
import textwrap
from pathlib import Path

import pytest

# The URL the operator screenshotted. Everything else in this file is derived
# from it; this is the only literal about routing.
SCHOLAR_URL = "/apps/scholar/"

# The contract, in one place: Search leads. A new visitor has an empty Library,
# so leading with it opens the app on a blank list; Search is the thing they can
# act on with no prior state, and it is how anything gets INTO the Library.
FIRST_TAB = "search"

_NAV_RE = re.compile(
    r'<nav[^>]*class="[^"]*scholar-tabs[^"]*"[^>]*>(.*?)</nav>',
    re.DOTALL,
)
_DATA_TAB_RE = re.compile(r'data-tab="([a-z0-9_-]+)"')


# ---------------------------------------------------------------------------
# Derivation helpers: URL -> view -> template name -> file on disk -> tab order
# ---------------------------------------------------------------------------
def _view_for(url):
    """The view callable the URLconf actually dispatches ``url`` to."""
    from django.urls import resolve

    return inspect.unwrap(resolve(url).func)


def _template_names_rendered_by(view):
    """Template names passed to ``render(...)`` in the view's own source.

    Read out of the view's AST rather than by executing it, so this needs no
    database, no session and no authenticated user — a view that 302s or 403s
    for the test client cannot make this test pass for the wrong reason.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(view)))
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if called != "render":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and str(arg.value).endswith(".html"):
                names.append(arg.value)
    return names


def _template_file(name):
    """Where Django's own loaders find ``name`` on disk."""
    from django.template.loader import get_template

    return Path(get_template(name).origin.name)


def _tab_order(html):
    """Tab ids, in document order, of the first ``nav.scholar-tabs`` in ``html``.

    Returns ``None`` when the markup declares no such nav.
    """
    match = _NAV_RE.search(html)
    if match is None:
        return None
    return _DATA_TAB_RE.findall(match.group(1))


def _scholar_app_dir():
    """The scholar app package directory, located by import, not by path."""
    import apps.workspace.scholar_app as scholar_app

    return Path(scholar_app.__file__).parent


def _templates_declaring_tabs():
    """Every scholar template that declares a hash-routed ``nav.scholar-tabs``.

    Keyed by path, valued by tab order. ``scholar_base.html`` declares a
    ``nav.scholar-tabs`` too but routes with ``{% url %}`` to separate pages and
    has no Library tab at all; it yields no ``data-tab`` ids and is therefore
    excluded on purpose, not by accident. ``test_the_sweep_is_not_vacuous``
    below fails if this sweep ever silently collapses to nothing.
    """
    found = {}
    for path in sorted(_scholar_app_dir().rglob("*.html")):
        order = _tab_order(path.read_text(encoding="utf-8"))
        if order:
            found[path] = order
    return found


def _ts_sources_declaring_tab_order():
    """TypeScript sources in the scholar app that hardcode a tab order."""
    static_dir = _scholar_app_dir() / "static"
    return sorted(
        p for p in static_dir.rglob("*.ts") if "TAB_ORDER" in p.read_text("utf-8")
    )


def _ts_const_list(src, const):
    match = re.search(rf"const\s+{const}\s*=\s*\[(.*?)\]", src, re.DOTALL)
    if match is None:
        return None
    return [a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', match.group(1))]


def _ts_const_str(src, const):
    match = re.search(rf"""const\s+{const}\s*=\s*["']([^"']+)["']""", src)
    return match.group(1) if match else None


def _rendered_four_tab_order():
    """The >=4-tab order declared by the template ``SCHOLAR_URL`` renders.

    ``[]`` when there is none — ``test_that_template_declares_a_scholar_tab_bar``
    is the check that this is never silently empty.
    """
    for name in _template_names_rendered_by(_view_for(SCHOLAR_URL)):
        order = _tab_order(_template_file(name).read_text("utf-8"))
        if order and len(order) >= 4:
            return order
    return []


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------
class TestTheRenderedScholarPageLeadsWithSearch:
    """Follow the route, then assert the order. This is the one that matters."""

    def test_the_url_resolves_to_a_view_that_renders_a_template(self):
        # Without this the assertions below could pass vacuously on an empty
        # template list — the same "gate that cannot fail" that let #616 ship.
        # Arrange
        view = _view_for(SCHOLAR_URL)
        # Act
        names = _template_names_rendered_by(view)
        # Assert
        assert names, f"{SCHOLAR_URL} -> {view!r} renders no template literal"

    def test_that_template_declares_a_scholar_tab_bar(self):
        # Arrange
        names = _template_names_rendered_by(_view_for(SCHOLAR_URL))
        # Act
        orders = {n: _tab_order(_template_file(n).read_text("utf-8")) for n in names}
        # Assert
        assert any(
            o and len(o) >= 2 for o in orders.values()
        ), f"no nav.scholar-tabs with data-tab ids in {orders}"

    def test_search_is_the_first_tab_of_the_rendered_template(self):
        # THE assertion. Derived end to end: URL -> URLconf -> view -> render()
        # -> Django loader -> file -> markup order. Reordering a template that
        # this route does not render cannot turn this green.
        # Arrange
        names = _template_names_rendered_by(_view_for(SCHOLAR_URL))
        # Act
        offenders = {}
        for name in names:
            path = _template_file(name)
            order = _tab_order(path.read_text("utf-8"))
            if order and order[0] != FIRST_TAB:
                offenders[str(path)] = order
        # Assert
        assert offenders == {}, (
            f"{SCHOLAR_URL} renders a tab bar that does not lead with "
            f"{FIRST_TAB!r}: {offenders}"
        )

    def test_search_precedes_library_in_the_rendered_template(self):
        # Stated separately from "search is first" so a failure report names the
        # operator's actual complaint rather than an index.
        # Arrange
        names = _template_names_rendered_by(_view_for(SCHOLAR_URL))
        # Act
        inverted = {}
        for name in names:
            path = _template_file(name)
            order = _tab_order(path.read_text("utf-8")) or []
            if {"search", "library"} <= set(order) and order.index(
                "search"
            ) > order.index("library"):
                inverted[str(path)] = order
        # Assert
        assert inverted == {}, f"Library still precedes Search in {inverted}"


class TestEveryCopyOfTheTabBarAgrees:
    """Duplicated tab definitions are why this bug survived a green PR."""

    def test_the_sweep_is_not_vacuous(self):
        # Arrange
        found = _templates_declaring_tabs()
        # Act
        count = len(found)
        # Assert
        assert count >= 2, f"expected several tab-bar copies, found {found}"

    def test_every_declared_tab_bar_leads_with_search(self):
        # Arrange
        found = _templates_declaring_tabs()
        # Act
        offenders = {
            str(p): o for p, o in found.items() if o and o[0] != FIRST_TAB
        }
        # Assert
        assert offenders == {}, f"tab bars not leading with {FIRST_TAB!r}: {offenders}"

    def test_the_four_tab_copies_are_identical(self):
        # The standalone page and the workspace SPA module pane are two live
        # surfaces of ONE app. They disagreed for a full day without anything
        # noticing.
        # Arrange
        found = {p: o for p, o in _templates_declaring_tabs().items() if len(o) >= 4}
        # Act
        distinct = {tuple(o) for o in found.values()}
        # Assert
        assert len(distinct) == 1, f"tab bars disagree: { {str(k): v for k, v in found.items()} }"


class TestTheTabSwitcherOpensOnSearch:
    """Markup order alone would still open the app on Library.

    ``scholar-tab-switcher.ts`` hardcodes both the accepted tab ids and the tab
    that opens when there is no hash (and unconditionally inside the unified
    workspace). #616 did not touch it, which is why the measured page reported
    ``activeTab: "library"`` even though the complaint was about position.
    """

    def test_a_typescript_source_declares_the_order(self):
        # Arrange
        static_dir = _scholar_app_dir() / "static"
        # Act
        sources = _ts_sources_declaring_tab_order()
        # Assert
        assert sources, f"no TS source under {static_dir} declares TAB_ORDER"

    def test_the_default_tab_is_search(self):
        # Arrange
        sources = _ts_sources_declaring_tab_order()
        # Act
        defaults = {
            str(p): _ts_const_str(p.read_text("utf-8"), "DEFAULT_TAB")
            for p in sources
        }
        offenders = {k: v for k, v in defaults.items() if v != FIRST_TAB}
        # Assert
        assert offenders == {}, f"DEFAULT_TAB is not {FIRST_TAB!r}: {offenders}"

    def test_the_typescript_order_matches_the_rendered_markup(self):
        # Cross-check: the JS whitelist and the template must be the same list,
        # so the two can never drift apart again in opposite directions.
        # Arrange
        markup = _rendered_four_tab_order()
        # Act
        offenders = {
            str(p): _ts_const_list(p.read_text("utf-8"), "TAB_ORDER")
            for p in _ts_sources_declaring_tab_order()
            if _ts_const_list(p.read_text("utf-8"), "TAB_ORDER") != markup
        }
        # Assert
        assert offenders == {}, f"TAB_ORDER != rendered markup {markup}: {offenders}"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
