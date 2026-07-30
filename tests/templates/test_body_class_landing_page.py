#!/usr/bin/env python3
"""The `landing-page` body class must key off WHICH PAGE RENDERS, not the session role.

Card hub-visitor-funnel-first-impression-20260730.

WHY THIS FILE EXISTS — a regression that shipped and that every existing test missed.

`static/shared/css/components/workspace-layout.css` gives `body.landing-page` two
opposite jobs:

    :140   body.landing-page .workspace-layout { display: none; }
    :152   body.landing-page .site-footer      { display: block; }

so the class means "the marketing page is rendering: hide the app shell, show the
footer". #499 applied it based on the SESSION ROLE
(`{% if not user.is_authenticated or is_visitor %}`) to fix a footer missing for
visitors on /landing/. That branch also covers `/` — and `/` is not the landing page
for a visitor: root_dispatch (repo_app/views/dispatch.py) redirects only
ROLE_ANONYMOUS to marketing and renders the app-launcher for every other role.

Result: every visitor's launcher carried `landing-page` and the whole shell was
hidden. Measured in a real browser on prod: 13 `.launcher-tile` elements present in
the DOM, `#workspace-layout` computed `display: none`, `main` 0x0, header and footer
the only visible things. A footer on one page traded for a blank workspace on another.

WHY THE EXISTING GUARDS DID NOT CATCH IT — this is the part worth keeping:
tests/apps/apps_app/test_launcher_guest_mode.py already asserted that a visitor at
`/` gets 200 and `is_guest_launcher is True`. Both stayed GREEN through the entire
regression, because status code and context say nothing about whether CSS then hides
what was rendered. A test that cannot observe visibility cannot defend it. These
tests assert on the body class — the one server-side output that decides it.

No mocks — real Django test DB + test client. One assertion per test (STX-TQ007).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings

BODY_TAG = re.compile(rb"<body\b[^>]*>", re.IGNORECASE | re.DOTALL)
CLASS_ATTR = re.compile(rb'class="([^"]*)"', re.IGNORECASE)

CSS_RULE_PATH = "static/shared/css/components/workspace-layout.css"


def _body_classes(content: bytes) -> set[str]:
    """Return the <body> element's class tokens.

    Parsed from the raw response rather than with an HTML parser on purpose:
    html.parser *recovers* malformed attributes that a browser would drop, so it can
    report a class the browser never sees. The raw attribute is what shipped.
    """
    tag = BODY_TAG.search(content)
    assert tag, "no <body> tag in response — the template did not render"
    attr = CLASS_ATTR.search(tag.group(0))
    if not attr:
        return set()
    return set(attr.group(1).decode().split())


@pytest.fixture
def visitor(django_user_model):
    """A pool visitor. The role is derived from the username by get_user_role()."""
    return django_user_model.objects.create_user(
        username="visitor-001", password="Password123!"
    )


@pytest.fixture
def readonly_visitor(django_user_model):
    return django_user_model.objects.create_user(
        username="readonly-visitor", password="Password123!"
    )


@pytest.fixture
def registered_user(django_user_model):
    return django_user_model.objects.create_user(
        username="regular-user", password="Password123!"
    )


class TestLandingPageClassIsPathBased:
    """`landing-page` appears iff the landing page is what renders."""

    # ---- THE REGRESSION ----------------------------------------------------

    @pytest.mark.django_db
    def test_visitor_at_root_does_not_get_landing_page_class(self, client, visitor):
        # Arrange: a pool visitor, whose "/" renders the app launcher
        client.force_login(visitor)
        # Act
        resp = client.get("/")
        # Assert — `landing-page` here would hide .workspace-layout entirely
        assert "landing-page" not in _body_classes(resp.content)

    @pytest.mark.django_db
    def test_readonly_visitor_at_root_does_not_get_landing_page_class(
        self, client, readonly_visitor
    ):
        # Arrange: a read-only visitor also lands on the launcher, not marketing
        client.force_login(readonly_visitor)
        # Act
        resp = client.get("/")
        # Assert
        assert "landing-page" not in _body_classes(resp.content)

    @pytest.mark.django_db
    def test_registered_user_at_root_does_not_get_landing_page_class(
        self, client, registered_user
    ):
        # Arrange: the case that always worked — pinned so it cannot regress too
        client.force_login(registered_user)
        # Act
        resp = client.get("/")
        # Assert
        assert "landing-page" not in _body_classes(resp.content)

    # ---- THE POSITIVE CASES ----------------------------------------------
    # These exist so the negative assertions above cannot pass VACUOUSLY. If
    # `landing-page` were renamed or dropped everywhere, every "not in" test would
    # still pass while the CSS contract silently broke. These prove the marker is
    # real and still produced.

    @pytest.mark.django_db
    def test_anonymous_at_landing_gets_landing_page_class(self, client):
        # Arrange: nobody logged in
        # Act
        resp = client.get("/landing/")
        # Assert — the marker must actually be emitted somewhere
        assert "landing-page" in _body_classes(resp.content)

    @pytest.mark.django_db
    def test_visitor_at_landing_gets_landing_page_class(self, client, visitor):
        # Arrange: a visitor viewing the marketing page — this is #499's real bug,
        # which must STAY fixed: their footer depends on this class.
        client.force_login(visitor)
        # Act
        resp = client.get("/landing/")
        # Assert
        assert "landing-page" in _body_classes(resp.content)

    # ---- THE SHELL MUST STILL BE CLAIMED --------------------------------

    @pytest.mark.django_db
    def test_visitor_at_root_still_gets_workspace_page_class(self, client, visitor):
        # Arrange: guards against "fixing" this by emitting no classes at all,
        # which would also satisfy every negative assertion above.
        client.force_login(visitor)
        # Act
        resp = client.get("/")
        # Assert
        assert "workspace-page" in _body_classes(resp.content)


class TestLandingPageClassContractStillExists:
    """Pin the CSS side, so a rename fails loudly instead of silently."""

    @pytest.mark.django_db
    def test_css_still_hides_workspace_layout_for_landing_page(self):
        # Arrange: the rule that makes the class dangerous is the reason the tests
        # above matter. If someone renames the class or drops this rule, the
        # negative assertions become vacuous — so assert the rule itself.
        css = (Path(settings.BASE_DIR) / CSS_RULE_PATH).read_text(encoding="utf-8")
        # Act
        normalised = re.sub(r"\s+", " ", css)
        # Assert
        assert "body.landing-page .workspace-layout { display: none" in normalised
