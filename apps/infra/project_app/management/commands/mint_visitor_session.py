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
create_visitor_pool), opens a real Django session authenticated as that user,
and prints the session key. The capture step injects that session key into the
browser as the ``sessionid`` cookie, so every photographed page renders as a
writable pooled visitor. REQUIRED_ROLE stays 'visitor' — nothing is weakened.

Prints ONLY the session key on stdout (the workflow redirects it to a file /
env var), so it is safe to capture.
"""

from __future__ import annotations

import pickle
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Mint a logged-in session for the first pooled visitor (visitor-NNN) "
        "and print its session key, for the Product Screenshots capture."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=2,
            help="Session lifetime in days (default 2 — covers the capture run).",
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

        # A real Django session authenticated as the visitor. Django's
        # AuthenticationMiddleware reads _auth_user_id/_auth_user_backend/
        # _auth_user_hash on every request, so the browser that carries this
        # sessionid renders as `visitor` (get_user_role: username startswith
        # 'visitor-').
        session = Session()
        session.session_data = pickle.dumps(
            {
                "_auth_user_id": str(visitor.pk),
                "_auth_user_backend": "django.contrib.auth.backends.ModelBackend",
                "_auth_user_hash": visitor.get_session_auth_hash(),
            }
        )
        session.expire_date = timezone.now() + timedelta(days=options["days"])
        session.save()

        # stdout = the session key and nothing else.
        print(session.session_key)
