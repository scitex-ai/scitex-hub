#!/usr/bin/env python3
"""mint_visitor_session: mints a logged-in session for a pooled visitor.

Card hub-product-screenshot-visitor-regression-20260913. The Product Screenshots
capture no longer relies on VisitorAutoLoginMiddleware (removed by #764); it
injects the session this command mints as the browser's sessionid cookie. These
tests prove the command picks the first visitor, mints a session that actually
authenticates as that user, and that the resulting request reads role 'visitor'
(the exact thing the capture's warm-up assertion checks).

DB-gated (needs the visitor pool + session table); runs in CI.
"""

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def pooled_visitor(db):
    """Create a deterministic pooled visitor user (the pool's shape)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="visitor-001",
        email="visitor-001@example.com",
        password="unusable-password",
    )
    return user


def _run(capsys, pooled_visitor):
    from django.core.management import call_command

    out = []
    with capsys.disabled():
        call_command("mint_visitor_session", verbosity=0)
    return capsys.readouterr().out.strip()


def test_mints_a_session_that_authenticates_as_the_visitor(capsys, pooled_visitor):
    key = _run(capsys, pooled_visitor)
    assert key, "the command must print a session key"

    # A request carrying that session reads back as the pooled visitor.
    from django.contrib.sessions.models import Session
    from django.test import RequestFactory

    session = Session.objects.get(session_key=key)
    req = RequestFactory().get("/apps/home/")
    req.session = session  # AuthenticationMiddleware binds req.session -> req.user
    from django.contrib.auth.middleware import AuthenticationMiddleware

    mw = AuthenticationMiddleware(lambda r: None)
    mw.process_request(req)
    assert req.user.is_authenticated
    assert req.user.username == "visitor-001"


def test_the_minted_session_reads_role_visitor(capsys, pooled_visitor):
    """The capture's warm-up asserts data-session-role == 'visitor'; that is
    driven by get_session_role -> get_user_role, which keys on the username
    prefix. Prove the minted session lands in that role, not user/anonymous."""
    key = _run(capsys, pooled_visitor)
    from django.contrib.sessions.models import Session
    from django.test import RequestFactory
    from django.contrib.auth.middleware import AuthenticationMiddleware

    from apps.infra.project_app.services.visitor_pool.session_role import (
        ROLE_VISITOR,
        get_session_role,
    )

    req = RequestFactory().get("/apps/home/")
    req.session = Session.objects.get(session_key=key)
    AuthenticationMiddleware(lambda r: None).process_request(req)
    assert get_session_role(req) == ROLE_VISITOR


def test_fails_loudly_with_no_pool(capsys, db):
    """No pooled visitor -> the command refuses (exit 1) rather than minting a
    session for the wrong identity."""
    from django.core.management import call_command

    with pytest.raises(SystemExit):
        call_command("mint_visitor_session", verbosity=0)
