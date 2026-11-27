# -*- coding: utf-8 -*-
# File: apps/infra/auth_app/management/commands/check_mail_delivery.py
"""Fail loudly when this deployment cannot send mail (scitex-hub#1234).

    python manage.py check_mail_delivery                 # connect + login, send nothing
    python manage.py check_mail_delivery --send-to ADDR  # also send one test message

Without ``--send-to`` the command sends no mail, so it is safe to run after every
deploy (``make ENV=<env> restart`` does). Exit status 1 means verification
codes, inquiry notifications and mail_admins alerts would all fail right now.

Output names the backend, the stage reached and an SMTP status code. It never
prints the account name, the password or the server's free-text reply.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from apps.infra.auth_app.mail_health import probe_mail_backend


class Command(BaseCommand):
    help = (
        "Check that the configured mail backend accepts a login (sends nothing), "
        "optionally sending one test message. Exit 1 on failure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-to",
            default="",
            help="Also send one plain-text test message to this address.",
        )

    def handle(self, *args, **options):
        probe = probe_mail_backend()
        if not probe.ok:
            raise CommandError(
                probe.summary()
                + ". Verification codes and notifications cannot be delivered. "
                "Check the SCITEX_HUB_EMAIL_* settings for this environment."
            )
        self.stdout.write(self.style.SUCCESS(probe.summary()))

        to_addr = (options.get("send_to") or "").strip()
        if not to_addr:
            return
        try:
            sent = send_mail(
                subject="SciTeX Hub mail delivery check",
                message=(
                    "This is an automated delivery check from "
                    f"{getattr(settings, 'SITE_URL', 'SciTeX Hub')}.\n"
                    "No action is needed.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_addr],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 -- report the class, then fail
            raise CommandError(f"test send FAILED ({type(exc).__name__})") from None
        if not sent:
            raise CommandError("test send FAILED (backend accepted 0 messages)")
        self.stdout.write(self.style.SUCCESS("test message accepted by the backend"))
