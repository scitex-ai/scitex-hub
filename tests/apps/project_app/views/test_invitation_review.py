#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An invitation is reviewed and accepted explicitly — never joined by opening it.

Card: hub-project-collaboration-invite-links-20260917.
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §9 — "A recipient signs in or
creates and verifies their own SciTeX account, reviews the project and role, then
explicitly accepts. Opening the link or completing signup does not silently join
the project." Also: "The link never reveals project files", every collaborator has
an individual identity, and tokens must not leak.

Measured before this change: `accept_invitation` was a `@login_required` view that
called `invitation.accept()` on ANY request, including a plain GET — one page
load, one prefetch or one link scanner created the membership and redirected the
recipient into the project. There was no review step at all, and no noindex /
no-referrer / no-store on a URL that carries the token.

The template-render tests need no database; the route tests are gated for CI.
"""

from __future__ import annotations

import re

import pytest
from django.template.loader import render_to_string

TEMPLATE = "project_app/invitation_review.html"

RECIPIENT = {
    "state": "review",
    "token": "tok",
    "project_name": "Hippocampus Replay",
    "inviter_name": "alice",
    "role": "Collaborator",
    "permission_level": "Read/Write",
    "expires_at": "2026-09-24 00:00 UTC",
    "accept_url": "/invitations/tok/accept/",
    "decline_url": "/invitations/tok/decline/",
}


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# ---------------------------------------------------------------------------
# the review screen (no database)
# ---------------------------------------------------------------------------


def test_the_recipient_reviews_the_project_role_and_expiry_before_deciding():
    html = render_to_string(TEMPLATE, RECIPIENT)

    assert 'data-invite-review="true"' in html
    assert 'data-invite-state="review"' in html
    for fact in ("project", "inviter", "role", "access", "expires"):
        assert f'data-invite-fact="{fact}"' in html, f"the review omits {fact}"
    text = _text(html)
    assert "Hippocampus Replay" in text
    assert "alice" in text
    assert "Collaborator" in text
    assert "Read/Write" in text


def test_accepting_and_declining_are_explicit_posts_not_links():
    html = render_to_string(TEMPLATE, RECIPIENT)

    accept = re.search(r'<form[^>]*action="([^"]*)"[^>]*>(.*?)</form>', html, re.S)
    assert accept, "no accept form at all — accepting must not be a link"
    assert accept.group(1) == "/invitations/tok/accept/"
    assert 'method="post"' in accept.group(0).lower()
    # CSRF presence is asserted on the real request path (TestInvitationRoute): a
    # bare render_to_string has no request, so {% csrf_token %} legitimately renders
    # empty here and asserting it would only ever test the harness.
    assert 'data-invite-action="accept"' in accept.group(0)

    assert re.search(
        r'<form[^>]*action="/invitations/tok/decline/"[^>]*method="post"|<form[^>]*method="post"[^>]*action="/invitations/tok/decline/"',
        html,
    ), "declining must POST too"
    assert 'data-invite-action="decline"' in html


def test_the_review_says_nothing_is_shared_yet():
    text = _text(render_to_string(TEMPLATE, RECIPIENT)).lower()

    assert "only after you accept" in text, (
        "the screen does not tell the recipient that acceptance is what shares the project"
    )
    # No project content before authorization: no file/activity/member surfaces.
    for forbidden in ("data-file", "file-tree", "commit", "members"):
        assert forbidden not in text, f"the review leaks a {forbidden} surface"


def test_the_page_is_not_indexable():
    html = render_to_string(TEMPLATE, RECIPIENT)

    assert re.search(r'<meta[^>]+name="robots"[^>]+content="noindex,\s*nofollow"', html), (
        "an invitation URL must carry noindex/nofollow"
    )


@pytest.mark.parametrize(
    "state,expected",
    [
        ("not_yours", "sent to a different SciTex account"),
        ("expired", "time-limited"),
        ("already_accepted", "already accepted"),
        ("already_declined", "no longer pending"),
    ],
)
def test_every_unhappy_state_explains_itself(state, expected):
    html = render_to_string(TEMPLATE, {"state": state, "token": "tok"})

    assert f'data-invite-state="{state}"' in html
    assert expected.lower() in _text(html).lower()


def test_a_stranger_is_told_nothing_about_the_project():
    """The link may be forwarded; a non-recipient must learn nothing from it."""
    html = render_to_string(TEMPLATE, {"state": "not_yours", "token": "tok"})

    for leak in ("Hippocampus Replay", "alice", "Collaborator", "Read/Write"):
        assert leak not in html, f"the not-yours state reveals {leak}"
    assert 'data-invite-fact=' not in html
    assert 'data-invite-action="accept"' not in html


# ---------------------------------------------------------------------------
# the route (database gate, runs in CI)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvitationRoute:
    def _invitation(self, *, status="pending", expired=False, recipient="bob", actor="alice"):
        from datetime import timedelta

        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.infra.project_app.models import Project, ProjectInvitation

        User = get_user_model()
        alice = User.objects.create_user(username=actor, password="x")
        bob = User.objects.create_user(username=recipient, password="x")
        project = Project.objects.create(
            name="Hippocampus Replay", slug="hippocampus-replay", owner=alice,
            visibility="private",
        )
        invitation = ProjectInvitation.objects.create(
            project=project, invited_user=bob, invited_by=alice,
            role="collaborator", permission_level="write",
            expires_at=timezone.now() + (timedelta(days=-1) if expired else timedelta(days=7)),
        )
        if status != "pending":
            invitation.status = status
            invitation.save(update_fields=["status"])
        return invitation, bob

    def test_opening_the_link_does_not_join_the_project(self):
        from django.test import Client

        from apps.infra.project_app.models import ProjectMembership

        invitation, bob = self._invitation()
        client = Client()
        client.force_login(bob)

        response = client.get(f"/invitations/{invitation.token}/accept/")

        assert response.status_code == 200
        assert b'data-invite-review="true"' in response.content
        # On the real request path the accept form must carry a CSRF token.
        assert b"csrfmiddlewaretoken" in response.content
        invitation.refresh_from_db()
        assert invitation.status == "pending", "a GET joined the project"
        assert ProjectMembership.objects.filter(project=invitation.project, user=bob).count() == 0

        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
        assert response.headers["Referrer-Policy"] == "no-referrer"

    def test_posting_accept_joins_and_lands_in_the_project(self):
        from django.test import Client

        from apps.infra.project_app.models import ProjectMembership

        invitation, bob = self._invitation()
        client = Client()
        client.force_login(bob)

        response = client.post(f"/invitations/{invitation.token}/accept/")

        assert response.status_code in (302, 303)
        invitation.refresh_from_db()
        assert invitation.status == "accepted"
        assert ProjectMembership.objects.filter(project=invitation.project, user=bob).exists()
        assert response["Location"] == f"/{invitation.project.owner.username}/{invitation.project.slug}/"

    def test_a_stranger_cannot_accept_and_sees_no_project_details(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        invitation, _bob = self._invitation()
        stranger = get_user_model().objects.create_user(username="mallory", password="x")
        client = Client()
        client.force_login(stranger)

        response = client.get(f"/invitations/{invitation.token}/accept/")
        assert response.status_code == 200
        assert b'data-invite-state="not_yours"' in response.content
        assert b"Hippocampus Replay" not in response.content

        client.post(f"/invitations/{invitation.token}/accept/")
        invitation.refresh_from_db()
        assert invitation.status == "pending"

    def test_an_expired_invitation_cannot_be_accepted(self):
        from django.test import Client

        from apps.infra.project_app.models import ProjectMembership

        invitation, bob = self._invitation(expired=True)
        client = Client()
        client.force_login(bob)

        response = client.get(f"/invitations/{invitation.token}/accept/")
        assert b'data-invite-state="expired"' in response.content

        client.post(f"/invitations/{invitation.token}/accept/")
        invitation.refresh_from_db()
        assert invitation.status == "pending"
        assert ProjectMembership.objects.filter(project=invitation.project, user=bob).count() == 0

    def test_declining_also_requires_a_post(self):
        from django.test import Client

        invitation, bob = self._invitation()
        client = Client()
        client.force_login(bob)

        client.get(f"/invitations/{invitation.token}/decline/")
        invitation.refresh_from_db()
        assert invitation.status == "pending", "a GET declined the invitation"

        client.post(f"/invitations/{invitation.token}/decline/")
        invitation.refresh_from_db()
        assert invitation.status == "declined"


# ---------------------------------------------------------------------------
# the owner's side: a copyable link and the three steps (no database)
# ---------------------------------------------------------------------------

OWNER_PANEL = "project_app/projects/settings_partials/settings_collaborators.html"


class _All(list):
    """Stands in for a related manager: the partial asks for `.all`."""

    @property
    def all(self):
        return list(self)

    @property
    def count(self):
        return len(self)


class _Invitation:
    def __init__(self, token, username, status="pending", role="collaborator",
                 permission_level="write", expires_at="2026-09-24 00:00 UTC"):
        self.token = token
        self.invited_user = type("U", (), {"username": username})()
        self.status = status
        self.role = role
        self.permission_level = permission_level
        self.expires_at = expires_at


def _owner_panel(invitations):
    project = type("P", (), {
        "invitations": _All(invitations),
        "memberships": _All([]),
    })()
    return render_to_string(OWNER_PANEL, {"project": project})


def test_the_owner_can_copy_the_invitation_link():
    html = _owner_panel([_Invitation("abc123", "bob")])

    assert 'data-invite-link="abc123"' in html, "no copyable link for the pending invite"
    assert 'value="/invitations/abc123/accept/"' in html
    assert 'data-copy-invite-link="invite-link-abc123"' in html, "no copy control"
    assert re.search(r'readonly', html), "the link field must be readonly"


def test_the_panel_states_the_three_steps_and_the_limits_of_the_link():
    html = _owner_panel([_Invitation("abc123", "bob")])
    text = _text(html).lower()

    assert 'data-invite-steps="true"' in html
    assert "sign in" in text and "create and verify" in text
    assert "review the project and the role" in text
    assert "opening the link does not join them" in text
    assert "only the invited account can accept" in text


def test_the_panel_shows_the_role_access_and_expiry_next_to_the_link():
    html = _owner_panel([_Invitation("abc123", "bob")])
    text = _text(html)

    assert "Collaborator" in text and "Write" in text
    assert "2026-09-24 00:00 UTC" in text


def test_a_non_pending_invitation_exposes_no_token():
    """Accepted/declined invites must not keep handing out a redeemable URL."""
    html = _owner_panel([_Invitation("gone999", "carol", status="accepted")])

    assert "gone999" not in html, "a non-pending invitation still renders its token"
    assert "data-invite-link=" not in html


# EOF
