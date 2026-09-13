"""Mint a logged-in session for a pooled visitor and print its session key.

Used by the Product Screenshots capture (card
hub-product-screenshot-visitor-regression-20260913). The visitor-retirement
merge (#764) removed VisitorAutoLoginMiddleware, which used to auto-pool an
anonymous browser into a writable visitor slot. The capture's Playwright
context now needs an EXPLICIT, deterministic visitor session; the conftest
mints it in-process (``mint_visitor_session_key``) and injects the key as the
``sessionid`` cookie, so every photographed page renders as a writable pooled
visitor. REQUIRED_ROLE stays 'visitor' — nothing is weakened.

``mint_visitor_session_key`` is the reusable core; this command is a thin
wrapper that prints it (for manual use). The conftest calls the function
DIRECTLY rather than parsing this command's stdout, because a management
command's stdout also carries settings-import-time prints (e.g. the Redis
fallback warning), so capturing it as the key yields a corrupt >40-char value
the server cannot resolve — the exact failure of run 34730332276.

CRITICAL: the session MUST be written through ``settings.SESSION_ENGINE``. On
this deployment that is the cache backend (Redis when reachable, otherwise the
settings fall back to the db backend) — NOT a raw ORM ``Session`` row, which is
invisible to a cache-backed engine.
"""

from __future__ import annotations

import importlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def mint_visitor_session_key(days: int = 2) -> str:
    """Mint and return a real session key authenticated as the first pooled
    visitor (visitor-NNN). Raises when no pool exists or the engine does not
    persist the key.

    The session is written through ``settings.SESSION_ENGINE`` (the same engine
    the running server reads), so it resolves identically in-process and
    server-side. ``days`` is retained for API symmetry; the session engine's
    own expiry applies.
    """
    User = get_user_model()
    visitor = (
        User.objects.filter(username__startswith="visitor-")
        .order_by("username")
        .first()
    )
    if visitor is None:
        raise LookupError(
            "No pooled visitor user (visitor-NNN) found. Run "
            "`create_visitor_pool` + `reconcile_visitor_slots` + "
            "`assert_visitor_pool_ready` first."
        )

    engine = importlib.import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore()
    store["_auth_user_id"] = str(visitor.pk)
    store["_auth_user_backend"] = (
        "django.contrib.auth.backends.ModelBackend"
    )
    store["_auth_user_hash"] = visitor.get_session_auth_hash()
    store.create()

    if not store.session_key:
        raise RuntimeError(
            f"Session for {visitor.username} was not persisted by the "
            f"{settings.SESSION_ENGINE} engine — the capture would photograph "
            "as anonymous."
        )
    return store.session_key


class Command(BaseCommand):
    help = (
        "Mint a logged-in session for the first pooled visitor (visitor-NNN) "
        "and write its session key, for the Product Screenshots capture."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help=(
                "Write the session key to this file (one line) instead of "
                "stdout. PREFERRED for the CI workflow: a management command's "
                "stdout also carries settings-import-time prints, so capturing "
                "stdout as the key corrupts it (run 34730332276, len=150). "
                "Writing the key straight to a file has no such boundary."
            ),
        )

    def handle(self, *args, **options):
        key = mint_visitor_session_key()
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as fh:
                fh.write(key + "\n")
            self.stdout.write(f"wrote visitor session key to {options['output']}")
        else:
            # Manual-use path: stdout = the key and nothing else.
            print(key)
