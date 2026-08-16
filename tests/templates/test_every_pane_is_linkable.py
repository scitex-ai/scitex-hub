#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every root-mounted workspace pane must be reachable by a REAL LINK.

THE DEFECT, reported by the operator on 2026-08-16 as
「このページでてきてないのもったいないです」 — https://scitex.ai/chat/ is a good
page that nobody can find. He was screenshotting it for a grant application
and could not navigate to it.

Measured cause: on a DESKTOP viewport there was not one ``<a href="/chat/">``
anywhere on the site. The three root-mounted panes

    path("chat/",    root_dispatch, name="pane-chat",    kwargs={"pane": "chat"})
    path("console/", root_dispatch, name="pane-console", kwargs={"pane": "console"})
    path("files/",   root_dispatch, name="pane-files",   kwargs={"pane": "editor"})

were offered in the workspace sidebar as ``<button data-pane="chat">`` — a
client-side pane switch that ``sidebar/index.ts`` follows with

    history.pushState({ pane: paneId }, "", "/chat/")

A pushState URL exists only for someone who is ALREADY inside the workspace and
has already clicked. It is invisible to a crawler, to the browser's own link
surfaces, to "copy link address", and to anyone reading the page rather than
operating it. The only ``<a href="/chat/">`` on the site lived in the mobile
dock (``launcher.html:87``, ``display:none`` above 767px) and the mobile
hamburger menu (``global_header.html:818``) — both mobile-only.

WHY A DERIVED TEST AND NOT THREE ASSERTIONS. This is the third time this shape
of bug has landed on this board: #618 (``/tokushoho/`` misclassified because it
was missing from a hand-kept ``_NON_USER_PREFIXES``) and #621 (all three panes
missing from a hand-kept ``PATH_LABELS``, so the browser tab named the project
instead of the app). Each time the fix was "add the missing entry", and each
time the NEXT omission was free to happen just as silently.

So the pane set is DERIVED from ``config/urls.py``: a pane is a root ``path()``
carrying a ``pane`` kwarg, which is exactly how
``tests/config/test_every_pane_names_its_tab.py`` identifies one. A fourth pane
mounted tomorrow without a nav link fails HERE, naming its own route in the
failure message.

WHY THE URLCONF IS READ AS SOURCE AND NOT THROUGH ``get_resolver()``. The
sibling guard uses the live resolver, which is stronger where it can run —
but it can only run where the whole Django settings chain imports, and that
chain pulls ``scitex``, ``celery`` and every mounted app. A nav guard that can
only be executed inside a fully provisioned app container is a guard whose red
nobody ever watches; this one was in fact developed in a container where the
sibling could not be executed at all. ``ast`` gives the same two facts (route,
url name) from the same file with no imports, so this file runs anywhere the
repo is checked out. The two guards agree on what "a pane" is on purpose: a
pane must not be able to satisfy one and evade the other.

WHY ANCHORS SPECIFICALLY, AND NOT "the sidebar mentions chat". The pre-fix
markup DID carry ``data-pane="chat"`` in the sidebar. A test that swept for
pane ids, for the word "Chat", or for ``.sidebar-item`` elements would have
been GREEN throughout the entire period the operator could not find the page.
The property that was actually missing is a resolvable ``href`` on an ``<a>``,
so that is the only thing this file looks for; ``<button>`` elements are
deliberately not collected, and ``test_a_button_is_not_counted_as_a_link``
exists to keep that distinction from eroding.

WHAT THIS FILE DOES NOT COVER. It asserts the link EXISTS in the sidebar, which
is a signed-in surface. It says nothing about anonymous visitors: ``/chat/``
answers 302 -> ``/landing/`` for them (``repo_app/views/dispatch.py:52-53``),
and whether that should change is a product decision with inference-cost and
abuse implications, not a test's to make. It also does not assert visibility —
see ``test_footer_visible_by_default.py`` for why presence and visibility are
different questions.

No mocks. One assertion per test (STX-TQ007).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

#: Anchored on THIS FILE, deliberately, and not on ``settings.BASE_DIR``.
#: Under the editable install used here, ``config`` can resolve to the MAIN
#: checkout while pytest collects a linked worktree's tests — so BASE_DIR would
#: read a different tree than the one under review and report green on code
#: nobody changed. The test file is always in the tree being tested.
REPO = Path(__file__).resolve().parents[2]

#: The URLconf that mounts the panes.
URLCONF = "config/urls.py"

#: The desktop workspace navigation. This is the surface a signed-in user
#: looks at on every page of the app shell, and the only one that is present
#: above the 767px mobile breakpoint.
SIDEBAR_TEMPLATE = "templates/global_base_partials/workspace_sidebar.html"

#: An ``href`` on an ANCHOR open tag. ``[^>]*?`` deliberately refuses to cross
#: a ``>`` so the sweep cannot run past one tag into the next; Django's
#: ``{% if %}`` guards inside these attributes contain no ``>``.
ANCHOR_HREF = re.compile(r"<a\b[^>]*?href=\"([^\"]*)\"", re.DOTALL)

#: ``href="{% url 'pane-chat' %}"`` is as good an answer as ``href="/chat/"``.
#: Resolving it against the derived pane list keeps this guard from failing the
#: day someone reasonably migrates the template to reverse() — a false failure
#: teaches people to delete guards.
URL_TAG = re.compile(r"^\{%\s*url\s+['\"]([\w:.-]+)['\"]\s*%\}$")

#: A route the URLconf does not mount. Negative control against a sweep that
#: has degenerated into "yes".
UNMOUNTED_ROUTE = "/definitely-not-a-pane/"

#: Comment forms that must be removed BEFORE the anchor sweep runs. This is
#: not tidiness — it is the difference between a guard and a decoration. The
#: fix's own explanatory comment in the sidebar quotes the markup it is about
#: (`<a href="/chat/">`), so a sweep over the raw file matches the PROSE and
#: reports the page as linked no matter what the real markup says. The
#: footer guard strips CSS comments for exactly this reason and says so.
#: Django's ``{# ... #}`` does not nest and does not span lines.
COMMENT_FORMS = (
    re.compile(r"\{#.*?#\}"),
    re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL),
    re.compile(r"<!--.*?-->", re.DOTALL),
)


def _mounted_panes() -> list[tuple[str, str]]:
    """Return ``(route, url_name)`` for every root-mounted workspace pane.

    A pane is a ``path()`` call carrying a ``pane`` kwarg, which is how
    ``config/urls.py`` marks them — not a name match, which would drift the
    moment someone names one ``chat-pane`` instead of ``pane-chat``.
    """
    tree = ast.parse((REPO / URLCONF).read_text(encoding="utf-8"))
    panes: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "path"):
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        pane_kwargs = keywords.get("kwargs")
        if not isinstance(pane_kwargs, ast.Dict):
            continue
        keys = [k.value for k in pane_kwargs.keys if isinstance(k, ast.Constant)]
        if "pane" not in keys:
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        route = node.args[0].value
        # Skip parameterised variants like "chat/<uuid:session_token>/" — the
        # bare prefix is the one a nav item can link to.
        if "<" in route:
            continue
        name_node = keywords.get("name")
        name = name_node.value if isinstance(name_node, ast.Constant) else "<unnamed>"
        panes.append(("/" + route, name))
    return panes


def _sidebar_source() -> str:
    return (REPO / SIDEBAR_TEMPLATE).read_text(encoding="utf-8")


def _linked_hrefs(
    template_source: str, by_name: dict[str, str] | None = None
) -> set[str]:
    """Every destination the sidebar offers as a real ``<a href>``.

    ``{% url 'name' %}`` values are resolved through ``by_name`` (the same
    pane list derived from the URLconf); anything that still carries template
    syntax after that — a loop variable such as ``{{ mod.get_url }}`` — is
    dropped, because this guard can only speak about destinations that are
    knowable without a request.
    """
    by_name = by_name or {}
    for comment in COMMENT_FORMS:
        template_source = comment.sub("", template_source)
    hrefs = set()
    for raw in ANCHOR_HREF.findall(template_source):
        href = raw.strip()
        tag = URL_TAG.match(href)
        if tag:
            resolved = by_name.get(tag.group(1))
            if resolved:
                hrefs.add(resolved)
            continue
        if "{" in href:
            continue
        hrefs.add(href)
    return hrefs


def _sidebar_hrefs() -> set[str]:
    panes = _mounted_panes()
    return _linked_hrefs(_sidebar_source(), {name: route for route, name in panes})


class TestEveryPaneIsLinkable:
    def test_the_urlconf_actually_exposes_panes(self):
        """Vacuity check: an empty pane sweep would make the guard pass."""
        # Arrange
        panes = _mounted_panes()

        # Act
        count = len(panes)

        # Assert
        assert count > 0, f"found no pane routes in {URLCONF} — derivation broken"

    def test_the_sidebar_actually_contains_anchors(self):
        """Vacuity check: a parser that reads nothing must not be trusted.

        It would make the guard fail LOUD rather than pass, but a broken parser
        reporting every pane as unlinked is still a parser whose failure
        message lies about the cause. Assert it reads the file.
        """
        # Arrange
        hrefs = _sidebar_hrefs()

        # Act
        count = len(hrefs)

        # Assert
        assert count > 0, f"parsed no <a href> out of {SIDEBAR_TEMPLATE}"

    @pytest.mark.guards(
        defect=(
            "the root-mounted panes (/chat/, /console/, /files/) were offered "
            "in the workspace sidebar only as <button data-pane=...> "
            "client-side switches, so on a desktop viewport the site carried "
            "no <a href='/chat/'> at all and the operator could not navigate "
            "to, share, or have a crawler find the chat page"
        )
    )
    def test_every_mounted_pane_has_a_sidebar_link(self):
        # Arrange
        panes = _mounted_panes()
        hrefs = _sidebar_hrefs()

        # Act
        unlinked = [f"{route} ({name})" for route, name in panes if route not in hrefs]

        # Assert
        assert unlinked == [], (
            "these mounted panes have no <a href> in the workspace sidebar - a "
            "user can only reach them by clicking a client-side pane switch, "
            "so the URL is unshareable and invisible to crawlers: "
            f"{unlinked}"
        )

    @pytest.mark.guards(
        defect=(
            "/chat/ — the page the operator was screenshotting for a grant "
            "application — had no anchor on any desktop surface"
        )
    )
    def test_chat_is_reachable_by_href(self):
        # Arrange
        hrefs = _sidebar_hrefs()

        # Act
        present = "/chat/" in hrefs

        # Assert
        assert present, f'no <a href="/chat/"> in {SIDEBAR_TEMPLATE}'

    def test_a_button_is_not_counted_as_a_link(self):
        """Positive control for the ONE distinction this guard rests on.

        The pre-fix markup carried ``data-pane="chat"`` in the sidebar, so a
        sweep that accepted any element would have been green throughout the
        outage. If ``_linked_hrefs`` ever starts collecting buttons, this guard
        stops guarding anything and must fail here instead.
        """
        # Arrange
        markup = '<button class="sidebar-item" data-pane="chat">Chat</button>'

        # Act
        hrefs = _linked_hrefs(markup)

        # Assert
        assert hrefs == set()

    def test_an_anchor_is_counted_as_a_link(self):
        """Paired control: the sweep does read the shape the fix introduces."""
        # Arrange
        markup = '<a class="sidebar-item" href="/chat/" data-pane="chat">Chat</a>'

        # Act
        hrefs = _linked_hrefs(markup)

        # Assert
        assert hrefs == {"/chat/"}

    def test_a_django_commented_anchor_is_not_counted_as_a_link(self):
        """The near-miss that almost made this guard decorative.

        The fix's own comment in the sidebar QUOTES the markup it explains, so
        the raw file contains the string ``<a href="/chat/">`` inside a ``{# #}``
        whether or not the real anchor exists. A sweep that read the comment
        would have gone green on prose and stayed green if someone reverted the
        anchor. Same failure mode the footer guard documents for CSS comments.
        """
        # Arrange
        markup = '{# the site carried no <a href="/chat/"> at all #}'

        # Act
        hrefs = _linked_hrefs(markup)

        # Assert
        assert hrefs == set()

    def test_an_html_commented_anchor_is_not_counted_as_a_link(self):
        """Same hazard in the other comment syntax this template already uses."""
        # Arrange
        markup = '<!-- <a href="/chat/" class="sidebar-item">Chat</a> -->'

        # Act
        hrefs = _linked_hrefs(markup)

        # Assert
        assert hrefs == set()

    def test_an_unmounted_route_is_not_reported_as_linked(self):
        """Negative control: the sweep has not become a yes-machine."""
        # Arrange
        hrefs = _sidebar_hrefs()

        # Act
        present = UNMOUNTED_ROUTE in hrefs

        # Assert
        assert not present
