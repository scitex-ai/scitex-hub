#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every root-mounted workspace pane must be LINKABLE and must say WHO MAY SEE IT.

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

THE SECOND DEFECT, AND WHY THIS FILE NOW GUARDS TWO PROPERTIES. The first fix
turned all three sidebar items into ungated anchors. That derived the LINK SET
from the URLconf correctly and dropped the VISIBILITY RULE: ``/console/`` is a
terminal, gated to ``DEBUG or user.is_staff`` in the hamburger menu since
2026-07-21 and simply absent from the mobile dock, and the new sidebar anchor
put ``href="/console/"`` on every regular user's page.
``tests/apps/apps_app/test_header_mobile_menu_gate.py`` — whose whole job is
asserting that marker is ABSENT for a regular user — went red on all three
pytest legs. A structure derived from the URLconf must not discard per-item
authorization, so this guard now requires BOTH halves of a nav entry: a label
and a declared visibility.

WHY A DERIVED TEST AND NOT THREE ASSERTIONS. This is the third time this shape
of bug has landed on this board: #618 (``/tokushoho/`` misclassified because it
was missing from a hand-kept ``_NON_USER_PREFIXES``) and #621 (all three panes
missing from a hand-kept ``PATH_LABELS``, so the browser tab named the project
instead of the app). Each time the fix was "add the missing entry", and each
time the NEXT omission was free to happen just as silently.

So the pane set is DERIVED from ``config/urls.py``: a pane is a root ``path()``
carrying a ``pane`` kwarg, which is exactly how
``tests/config/test_every_pane_names_its_tab.py`` identifies one. A fourth pane
mounted tomorrow with no ``CorePane`` entry fails HERE, naming its own route —
and one declared without a visibility fails here too, rather than shipping the
Console leak again.

WHY THE URLCONF IS READ AS SOURCE AND NOT THROUGH ``get_resolver()``. The
sibling guard uses the live resolver, which is stronger where it can run —
but it can only run where the whole Django settings chain imports, and that
chain pulls ``scitex``, ``celery`` and every mounted app. A nav guard that can
only be executed inside a fully provisioned app container is a guard whose red
nobody ever watches; this one was in fact developed in a container where the
sibling could not be executed at all. ``ast`` gives the same facts (route, url
name, label, visibility) from the same files with no imports, so this file runs
anywhere the repo is checked out. The two guards agree on what "a pane" is on
purpose: a pane must not be able to satisfy one and evade the other.

WHY ANCHORS SPECIFICALLY, AND NOT "the sidebar mentions chat". The pre-fix
markup DID carry ``data-pane="chat"`` in the sidebar. A test that swept for
pane ids, for the word "Chat", or for ``.sidebar-item`` elements would have
been GREEN throughout the entire period the operator could not find the page.
The property that was actually missing is a resolvable ``href`` on an ``<a>``,
so that is the only thing this file looks for; ``<button>`` elements are
deliberately not collected, and ``test_a_button_is_not_counted_as_a_link``
exists to keep that distinction from eroding.

WHAT THIS FILE DOES NOT COVER. It reads SOURCE, so it proves the declaration is
complete and that the sidebar renders it as anchors; the RENDERED consequence —
a regular user's page carries ``/chat/`` and ``/files/`` but not ``/console/``
— is asserted against a real response in
``tests/templates/test_workspace_sidebar_pane_visibility.py`` and
``tests/apps/apps_app/test_header_mobile_menu_gate.py``. Visibility here also
means "offered in navigation", never "authorized": ``root_dispatch``
(``repo_app/views/dispatch.py``) serves ``/console/`` to any authenticated user
who types the URL, which predates all of this. It says nothing about anonymous
visitors either: ``/chat/`` answers 302 -> ``/landing/`` for them
(``dispatch.py:52-53``), and whether that should change is a product decision
with inference-cost and abuse implications, not a test's to make.

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

#: The single declaration of what each mounted pane is called, where it points,
#: and who may be offered it.
DECLARATION = "apps/infra/workspace_app/core_panes.py"

#: The desktop workspace navigation. This is the surface a signed-in user
#: looks at on every page of the app shell, and the only one that is present
#: above the 767px mobile breakpoint.
SIDEBAR_TEMPLATE = "templates/global_base_partials/workspace_sidebar.html"

#: The context variable the sidebar must iterate. Named here rather than
#: matched loosely so a rename has to be made deliberately in both places.
SIDEBAR_CONTEXT_VAR = "workspace_core_panes"

#: ``href="{% url 'pane-chat' %}"`` is as good an answer as ``href="/chat/"``.
#: Resolving it against the derived pane list keeps this guard from failing the
#: day someone reasonably migrates a template to reverse() — a false failure
#: teaches people to delete guards.
URL_TAG = re.compile(r"^\{%\s*url\s+['\"]([\w:.-]+)['\"]\s*%\}$")

#: An ``href`` on an ANCHOR open tag. ``[^>]*?`` deliberately refuses to cross
#: a ``>`` so the sweep cannot run past one tag into the next; Django's
#: ``{% if %}`` guards inside these attributes contain no ``>``.
ANCHOR_HREF = re.compile(r"<a\b[^>]*?href=\"([^\"]*)\"", re.DOTALL)

#: The core-pane loop: ``{% for <var> in workspace_core_panes %} ... {% endfor %}``.
#: The body is captured so the anchor sweep can be run against the LOOP BODY
#: alone — an anchor elsewhere in the sidebar (Home, a pinned module, Sign out)
#: must not be able to satisfy "the panes are rendered as links".
PANE_LOOP = re.compile(
    r"\{%\s*for\s+(\w+)\s+in\s+"
    + SIDEBAR_CONTEXT_VAR
    + r"\s*%\}(.*?)\{%\s*endfor\s*%\}",
    re.DOTALL,
)

#: A route the URLconf does not mount. Negative control against a sweep that
#: has degenerated into "yes".
UNMOUNTED_ROUTE = "/definitely-not-a-pane/"

#: Comment forms that must be removed BEFORE the anchor sweep runs. This is
#: not tidiness — it is the difference between a guard and a decoration. The
#: fix's own explanatory comment in the sidebar quotes the markup it is about,
#: so a sweep over the raw file matches the PROSE and reports the page as
#: linked no matter what the real markup says. The footer guard strips CSS
#: comments for exactly this reason and says so.
#: Django's ``{# ... #}`` does not nest and does not span lines.
COMMENT_FORMS = (
    re.compile(r"\{#.*?#\}"),
    re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL),
    re.compile(r"<!--.*?-->", re.DOTALL),
)


def _strip_comments(source: str) -> str:
    for comment in COMMENT_FORMS:
        source = comment.sub("", source)
    return source


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


def _declaration_tree() -> ast.Module:
    return ast.parse((REPO / DECLARATION).read_text(encoding="utf-8"))


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "literal"`` bindings, for resolving ``visibility=``.

    The declaration spells its rules as ``visibility=VISIBILITY_STAFF`` rather
    than a bare string, so the sweep has to resolve the name. Reading the
    bindings out of the same file (instead of hard-coding "everyone"/"staff"
    here) means a rule renamed there does not quietly stop being checked here.
    """
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value, str
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _known_visibilities() -> set[str]:
    """The closed set of rules, derived from the ``VISIBILITY_*`` constants."""
    constants = _module_constants(_declaration_tree())
    return {v for k, v in constants.items() if k.startswith("VISIBILITY_")}


def _declared_panes() -> dict[str, dict[str, str | None]]:
    """``url_name -> {route, label, visibility}`` from every ``CorePane(...)``.

    A field the declaration does not supply comes back as ``None`` rather than
    a default: "this pane never said who may see it" and "this pane said
    everyone" must not look the same to a guard whose entire subject is the
    difference.
    """
    tree = _declaration_tree()
    constants = _module_constants(tree)
    declared: dict[str, dict[str, str | None]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "CorePane"):
            continue
        fields: dict[str, str | None] = {}
        for keyword in node.keywords:
            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                fields[keyword.arg] = value.value
            elif isinstance(value, ast.Name):
                # e.g. visibility=VISIBILITY_STAFF; unresolvable names stay
                # None, which reads as "did not declare a known rule".
                fields[keyword.arg] = constants.get(value.id)
        url_name = fields.get("url_name")
        if not url_name:
            continue
        declared[url_name] = {
            "route": fields.get("route"),
            "label": fields.get("label"),
            "visibility": fields.get("visibility"),
        }
    return declared


def _sidebar_source() -> str:
    return (REPO / SIDEBAR_TEMPLATE).read_text(encoding="utf-8")


def _linked_hrefs(
    template_source: str, by_name: dict[str, str] | None = None
) -> set[str]:
    """Every destination a fragment offers as a real ``<a href>``.

    ``{% url 'name' %}`` values are resolved through ``by_name`` (the same
    pane list derived from the URLconf); anything that still carries template
    syntax after that — a loop variable such as ``{{ mod.get_url }}`` — is
    dropped, because this sweep can only speak about destinations that are
    knowable without a request.
    """
    by_name = by_name or {}
    template_source = _strip_comments(template_source)
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


def _pane_loop_anchor_hrefs() -> set[str]:
    """The raw ``href`` expressions on anchors INSIDE the core-pane loop.

    Returned unresolved (``{{ pane.route }}``) on purpose: the loop renders one
    anchor per declared pane, so what has to be proven here is that the loop
    body emits an ``<a>`` carrying the loop variable's route — not a literal,
    which would mean the list had been hand-copied back into the template.
    """
    source = _strip_comments(_sidebar_source())
    hrefs: set[str] = set()
    for var, body in PANE_LOOP.findall(source):
        for raw in ANCHOR_HREF.findall(body):
            href = raw.strip()
            if href == "{{ " + var + ".route }}":
                hrefs.add(href)
    return hrefs


class TestEveryPaneIsLinkable:
    def test_the_urlconf_actually_exposes_panes(self):
        """Vacuity check: an empty pane sweep would make the guard pass."""
        # Arrange
        panes = _mounted_panes()

        # Act
        count = len(panes)

        # Assert
        assert count > 0, f"found no pane routes in {URLCONF} — derivation broken"

    def test_the_declaration_actually_lists_panes(self):
        """Vacuity check: an empty declaration sweep must not read as green."""
        # Arrange
        declared = _declared_panes()

        # Act
        count = len(declared)

        # Assert
        assert count > 0, f"parsed no CorePane(...) entries out of {DECLARATION}"

    def test_the_sidebar_actually_contains_anchors(self):
        """Vacuity check: a parser that reads nothing must not be trusted.

        It would make the guard fail LOUD rather than pass, but a broken parser
        reporting every pane as unlinked is still a parser whose failure
        message lies about the cause. Assert it reads the file.
        """
        # Arrange
        hrefs = _linked_hrefs(_sidebar_source())

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
    def test_every_mounted_pane_is_declared_as_a_nav_item(self):
        # Arrange
        panes = _mounted_panes()
        declared = _declared_panes()

        # Act
        undeclared = [
            f"{route} ({name})" for route, name in panes if name not in declared
        ]

        # Assert
        assert undeclared == [], (
            "these mounted panes have no CorePane entry in "
            f"{DECLARATION}, so nothing renders a link to them and a user can "
            "only reach them by clicking a client-side pane switch - the URL "
            f"is unshareable and invisible to crawlers: {undeclared}"
        )

    def test_every_declared_pane_points_at_its_mounted_route(self):
        """A declaration that drifts from the URLconf links to a 404."""
        # Arrange
        declared = _declared_panes()

        # Act
        wrong = [
            f"{name}: declared {declared[name]['route']!r}, mounted {route!r}"
            for route, name in _mounted_panes()
            if name in declared and declared[name]["route"] != route
        ]

        # Assert
        assert wrong == [], f"declared routes disagree with {URLCONF}: {wrong}"

    def test_every_mounted_pane_declares_a_label(self):
        # Arrange
        declared = _declared_panes()

        # Act
        unlabelled = [
            name
            for _, name in _mounted_panes()
            if not (declared.get(name) or {}).get("label")
        ]

        # Assert
        assert unlabelled == [], (
            f"these panes have no label in {DECLARATION}, so no nav surface "
            f"can render them as anything a user could read: {unlabelled}"
        )

    @pytest.mark.guards(
        defect=(
            "PR #626 derived the sidebar link set from the URLconf and dropped "
            "the per-item visibility rule, publishing href='/console/' - a "
            "staff-gated developer terminal - to every regular user's page and "
            "turning MobileMenuDevItemGateTest red on all three pytest legs"
        )
    )
    def test_every_mounted_pane_declares_a_visibility(self):
        # Arrange
        declared = _declared_panes()
        known = _known_visibilities()

        # Act
        ungated = [
            f"{name} (declared {(declared.get(name) or {}).get('visibility')!r})"
            for _, name in _mounted_panes()
            if (declared.get(name) or {}).get("visibility") not in known
        ]

        # Assert
        assert ungated == [], (
            "these panes do not declare WHO MAY SEE THEM (expected one of "
            f"{sorted(known)} in {DECLARATION}). A pane whose visibility is "
            "unstated gets linked to everybody by default - which is exactly "
            f"how the staff-only console leaked: {ungated}"
        )

    @pytest.mark.guards(
        defect=(
            "/chat/ — the page the operator was screenshotting for a grant "
            "application — had no anchor on any desktop surface"
        )
    )
    def test_chat_is_offered_to_everyone(self):
        # Arrange
        declared = _declared_panes()

        # Act
        visibility = (declared.get("pane-chat") or {}).get("visibility")

        # Assert
        assert visibility == "everyone", (
            "/chat/ must be linked for every signed-in user - that is the "
            f"operator's 2026-08-16 ask - but it declares {visibility!r}"
        )

    @pytest.mark.guards(
        defect=(
            "the console terminal, staff-gated in the hamburger menu since "
            "2026-07-21 and absent from the mobile dock, became an ungated "
            "sidebar anchor"
        )
    )
    def test_console_is_offered_only_to_staff(self):
        # Arrange
        declared = _declared_panes()

        # Act
        visibility = (declared.get("pane-console") or {}).get("visibility")

        # Assert
        assert visibility == "staff", (
            "/console/ is a developer terminal and must stay behind the same "
            "DEBUG-or-is_staff gate global_header.html applies, but it "
            f"declares {visibility!r}"
        )

    def test_the_sidebar_renders_the_declared_panes_as_anchors(self):
        """The template must ITERATE the declaration, emitting one ``<a href>``.

        Not "the sidebar contains href='/chat/'": a literal would mean the pane
        list had been hand-copied back into the template, which is the state
        that leaked ``/console/``. What is asserted is the loop body carrying
        an anchor whose href IS the loop variable's route, so the rendered link
        set can only ever be what ``visible_core_panes()`` returns.
        """
        # Arrange
        hrefs = _pane_loop_anchor_hrefs()

        # Act
        count = len(hrefs)

        # Assert
        assert count == 1, (
            f"{SIDEBAR_TEMPLATE} must render exactly one <a> per item of the "
            f"{SIDEBAR_CONTEXT_VAR} loop, with href set to the loop "
            f"variable's .route; found {count} such anchors"
        )

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
        the raw file can contain ``<a href="/chat/">`` inside a ``{# #}``
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
        hrefs = _linked_hrefs(_sidebar_source())

        # Act
        present = UNMOUNTED_ROUTE in hrefs

        # Assert
        assert not present


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
