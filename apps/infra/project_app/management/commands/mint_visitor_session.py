"""Mint a logged-in session for a pooled visitor and print its session key.

Used by the Product Screenshots capture (card
hub-product-screenshot-visitor-regression-20260913). The visitor-retirement
merge (#764) removed VisitorAutoLoginMiddleware, which used to auto-pool an
anonymous browser into a writable visitor slot. The capture's Playwright
context had no stored state and relied on that auto-login, so it now
photographs as 'anonymous' and fails the (correct) data-session-role='visitor'
warm-up assertion.

This command restores the capture's identity DETERMINISTICALLY and EXPLICITLY:
it picks the first pooled visitor user (visitor-NNN, created by
create_visitor_pool), opens a REAL session authenticated as that user through
the CONFIGURED session engine, and prints the session key. The capture step
injects that key into the browser as the ``sessionid`` cookie, so every
photographed page renders as a writable pooled visitor. REQUIRED_ROLE stays
'visitor' — nothing is weakened.

CRITICAL (first fix did not hold): the session MUST be written through
``settings.SESSION_ENGINE`` — on this deployment that is the cache backend
(Redis in CI), NOT the database. An ORM ``Session`` row is invisible to a
cache-backed engine, so the browser carries a key the server cannot resolve
and the warm-up still reads 'anonymous'. ``SessionStore`` is the uniform API
across backends (db/cache/cache_db/file), so the command works on any of
them.

Prints ONLY the session key on stdout (the workflow redirects it to a file /
env var), so it is safe to capture.
"""

from __future__ import annotations

import importlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Mint a logged-in session for the first pooled visitor (visitor-NNN) "
        "and print its session key, for the Product Screenshots capture."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        visitor = (
            User.objects.filter(username__startswith="visitor-")
            .order_by("username")
            .first()
        )
        if visitor is None:
            self.stderr.write(
                "No pooled visitor user (visitor-NNN) found. Run "
                "`create_visitor_pool` + `reconcile_visitor_slots` + "
                "`assert_visitor_pool_ready` first."
            )
            raise SystemExit(1)

        # Open the session through the CONFIGURED engine (cache on this
        # deployment, not db) — see the module docstring. _auth_user_backend
        # must name a backend in settings.AUTHENTICATION_BACKENDS, which
        # includes django.contrib.auth.backends.ModelBackend.
        engine = importlib.import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store["_auth_user_id"] = str(visitor.pk)
        store["_auth_user_backend"] = (
            "django.contrib.auth.backends.ModelBackend"
        )
        store["_auth_user_hash"] = visitor.get_session_auth_hash()
        store.create()

        if not store.session_key:
            self.stderr.write(
                f"Session for {visitor.username} was not persisted by the "
                f"{settings.SESSION_ENGINE} engine — the capture would "
                "photograph as anonymous."
            )
            raise SystemExit(1)

        # stdout = the session key and nothing else.
        print(store.session_key)
