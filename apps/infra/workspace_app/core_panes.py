#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The root-mounted workspace panes, each with its OWN visibility rule.

WHY THIS FILE EXISTS. ``config/urls.py`` mounts three panes at the site
root — ``/chat/``, ``/console/``, ``/files/`` — and every navigation
surface then has to decide, separately, whether to offer each one. Until
now each surface decided by hand:

    * the mobile hamburger menu (``global_header.html``) wrapped Console in
      ``{% if DEBUG or user.is_staff %}`` and left Chat/Files open,
    * the mobile launcher dock (``launcher.html``) listed Chat and Files and
      simply omitted Console,
    * the desktop sidebar offered all three as ``<button data-pane=...>``
      client-side switches — no ``href`` at all, so the question of
      "who may be shown this link" never came up there.

PR #626 gave the sidebar real anchors so ``/chat/`` could finally be linked
to (operator 2026-08-16: 「このページでてきてないのもったいないです」). It derived
the LINK SET from the URLconf correctly and dropped the VISIBILITY RULE:
all three became ungated anchors, so ``href="/console/"`` appeared on every
regular user's page and ``MobileMenuDevItemGateTest`` — a guard whose entire
job is asserting a regular user's markup does not carry that marker — went
red on all three pytest legs. Deriving structure from the URLconf must not
mean discarding per-item authorization.

So the label and the visibility rule live TOGETHER, in one declaration, and
nav surfaces render what :func:`visible_core_panes` hands them instead of
each re-deciding. A fourth pane mounted tomorrow with no entry here fails
``tests/templates/test_every_pane_is_linkable.py``, which derives the pane
set from ``config/urls.py`` and requires a declaration carrying both a label
and a visibility for each — it cannot leak the way Console just did.

WHAT VISIBILITY IS, AND IS NOT. It governs whether a nav surface OFFERS the
pane. It is not an access control: ``root_dispatch`` (``repo_app/views/
dispatch.py``) redirects ``/console/`` to the workspace shell for any
authenticated user, so a regular user who types the URL still gets there.
That was true before this file existed and is not changed by it; if the
console pane should be authorization-gated, that is a separate decision on
the view, not on the menu.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Offered to every authenticated user. Chat and Files are ordinary
#: workspace surfaces — the mobile menu and the mobile dock have always
#: listed both without a gate.
VISIBILITY_EVERYONE = "everyone"

#: Offered when ``settings.DEBUG`` or ``user.is_staff`` — the exact gate
#: ``global_header.html`` already spells out for Console, Server Status and
#: Keyboard Shortcuts (operator 2026-07-21: keep developer-facing entries
#: out of an ordinary user's way).
VISIBILITY_STAFF = "staff"

#: The closed set. A typo'd rule must not silently read as "show it".
VISIBILITIES = frozenset({VISIBILITY_EVERYONE, VISIBILITY_STAFF})


@dataclass(frozen=True)
class CorePane:
    """One root-mounted pane as a navigation item.

    ``visibility`` has NO DEFAULT on purpose. A default would mean a pane
    added in a hurry inherits someone else's answer to "who may see this?",
    which is precisely how Console leaked. Omitting it is a TypeError at
    import time, and the URLconf-derived guard reports it before that.
    """

    route: str
    url_name: str
    pane: str
    label: str
    icon: str
    visibility: str
    default_active: bool = False

    def __post_init__(self) -> None:
        if self.visibility not in VISIBILITIES:
            raise ValueError(
                f"core pane {self.url_name!r} declares visibility "
                f"{self.visibility!r}; expected one of {sorted(VISIBILITIES)}"
            )
        if not self.label:
            raise ValueError(f"core pane {self.url_name!r} declares no label")


#: The declaration. Order is the sidebar order.
CORE_PANES: tuple[CorePane, ...] = (
    CorePane(
        route="/chat/",
        url_name="pane-chat",
        pane="chat",
        label="Chat",
        icon="fas fa-comment",
        # The operator's ask. /chat/ is the page he was screenshotting for a
        # grant application and could not navigate to.
        visibility=VISIBILITY_EVERYONE,
        # The sidebar has always shipped Chat pre-selected; the sidebar JS
        # takes over the active class from first click onwards.
        default_active=True,
    ),
    CorePane(
        route="/console/",
        url_name="pane-console",
        pane="console",
        label="Console",
        icon="fas fa-terminal",
        # A terminal is a developer/power tool. Same gate the hamburger menu
        # has carried since 2026-07-21, and the reason the mobile dock omits
        # it entirely. Guarded by
        # tests/apps/apps_app/test_header_mobile_menu_gate.py.
        visibility=VISIBILITY_STAFF,
    ),
    CorePane(
        route="/files/",
        url_name="pane-files",
        # NOTE: the pane id is "editor", not "files" — the route and the pane
        # id genuinely differ here (config/urls.py mounts "files/" with
        # kwargs={"pane": "editor"}), which is why both are declared.
        pane="editor",
        label="Files",
        icon="fas fa-folder",
        visibility=VISIBILITY_EVERYONE,
    ),
)


def is_pane_visible(pane: CorePane, request) -> bool:
    """Whether ``request``'s user may be OFFERED ``pane`` in navigation."""
    if pane.visibility == VISIBILITY_EVERYONE:
        return True
    # VISIBILITY_STAFF — validated by CorePane.__post_init__, so there is no
    # third branch that could fall through to "visible".
    from django.conf import settings

    user = getattr(request, "user", None)
    return bool(getattr(settings, "DEBUG", False)) or bool(
        getattr(user, "is_staff", False)
    )


def visible_core_panes(request) -> list[CorePane]:
    """The core panes this request's user may be offered, in sidebar order."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        # The sidebar itself only renders for authenticated users; returning
        # [] rather than the full list keeps that true of the data as well.
        return []
    return [pane for pane in CORE_PANES if is_pane_visible(pane, request)]


# EOF
