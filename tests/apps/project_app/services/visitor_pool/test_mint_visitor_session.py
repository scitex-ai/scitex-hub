#!/usr/bin/env python3
"""mint_visitor_session: mints a logged-in session for a pooled visitor.

Card hub-product-screenshot-visitor-regression-20260913. The Product Screenshots
capture no longer relies on VisitorAutoLoginMiddleware (removed by #764); it
injects the session this command mints as the browser's sessionid cookie. The
command writes through settings.SESSION_ENGINE (the cache backend on this
deployment, NOT the database) — a first cut that wrote an ORM Session row was
invisible to the running server and the warm-up still read 'anonymous'.

These tests prove, through the SAME engine the server reads:
  - the command mints a session that resolves to the pooled visitor,
  - a request carrying it reads get_session_role == 'visitor' (the exact thing
    the capture's warm-up assertion checks),
  - no pool -> the command refuses.

DB- + cache-gated (needs the visitor user + the session engine); runs in CI.
"""

import importlib

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def pooled_visitor(db):
    """A deterministic pooled visitor user (the pool's username shape)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="visitor-001",
        email="visitor-001@example.com",
        password="unusable-password",
    )


def _store_for(key):
    """A fresh session store bound to ``key`` on the CONFIGURED engine —
    exactly the path AuthenticationMiddleware uses to resolve a browser's
    sessionid cookie."""
    from django.conf import settings

    engine = importlib.import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore(session_key=key)
    store.load()
    return store


def _run(capsys):
    from django.core.management import call_command

    capsys.readouterr()  # clear
    call_command("mint_visitor_session", verbosity=0)
    return capsys.readouterr().out.strip()


def _request_as(session_store):
    """A request authenticated through the store, the way the server does it."""
    from django.contrib.auth.middleware import AuthenticationMiddleware
    from django.test import RequestFactory

    req = RequestFactory().get("/apps/home/")
    req.session = session_store
    AuthenticationMiddleware(lambda r: None).process_request(req)
    return req


def test_minted_session_resolves_to_the_visitor(capsys, pooled_visitor):
    from django.conf import settings

    key = _run(capsys)
    assert key, "the command must print a session key"

    store = _store_for(key)
    assert store["_auth_user_id"] == str(pooled_visitor.pk)
    assert store["_auth_user_backend"] in settings.AUTHENTICATION_BACKENDS

    req = _request_as(store)
    assert req.user.is_authenticated
    assert req.user.username == "visitor-001"


def test_minted_session_reads_role_visitor(capsys, pooled_visitor):
    """The capture's warm-up asserts data-session-role == 'visitor'; that value
    is driven by get_session_role -> get_user_role (username prefix). Prove the
    minted session lands in that role — not user/anonymous/readonly."""
    from apps.infra.project_app.services.visitor_pool.session_role import (
        ROLE_VISITOR,
        get_session_role,
    )

    key = _run(capsys)
    req = _request_as(_store_for(key))
    assert get_session_role(req) == ROLE_VISITOR


def test_fails_loudly_with_no_pool(capsys, db):
    """No pooled visitor -> the command refuses (exit 1) rather than minting a
    session for the wrong identity (e.g. a real account or readonly-visitor)."""
    from django.core.management import call_command

    with pytest.raises(SystemExit):
        call_command("mint_visitor_session", verbosity=0)


def test_output_file_writes_clean_resolvable_key(capsys, pooled_visitor, tmp_path):
    """The real CI path (run ae3aad2fb): `mint_visitor_session --output <file>`
    writes ONLY the session key to the file — no stdout pollution (the 150-char
    corruption that broke run 34730332276 came from capturing stdout) — and the
    file's key resolves to the pooled visitor through the configured engine. The
    command's internal round-trip (exists + auth-field match, d6b0ba86a) already
    ran before the file was written; re-verify here the way the server does."""
    from apps.infra.project_app.services.visitor_pool.session_role import (
        ROLE_VISITOR,
        get_session_role,
    )
    from django.core.management import call_command

    out_file = tmp_path / "screenshot_visitor_session"
    capsys.readouterr()
    call_command("mint_visitor_session", output=str(out_file), verbosity=0)

    key = out_file.read_text().strip()
    # Clean cookie-safe shape: non-empty alphanumeric 16-64 (accepts the 32-char
    # cache-backend and 40-char db-backend keys; rejects the 150-char stdout
    # value).
    assert key and 16 <= len(key) <= 64 and key.isalnum()

    store = _store_for(key)
    assert store["_auth_user_id"] == str(pooled_visitor.pk)
    assert _request_as(store).user.username == "visitor-001"
    assert get_session_role(_request_as(store)) == ROLE_VISITOR


def test_mint_refuses_when_session_not_persisted(capsys, pooled_visitor, monkeypatch):
    """Round-trip failure mode (d6b0ba86a): if the configured engine does not
    persist a key, the command raises RuntimeError (and never writes an output
    file) rather than hand the capture a session the server cannot resolve."""
    from django.conf import settings
    from django.core.management import call_command

    engine = importlib.import_module(settings.SESSION_ENGINE)

    class _NoPersistStore(engine.SessionStore):
        def create(self):  # simulate the backend failing to assign a key
            pass

    monkeypatch.setattr(engine, "SessionStore", _NoPersistStore)
    with pytest.raises(RuntimeError, match="was not persisted"):
        call_command("mint_visitor_session", verbosity=0)
