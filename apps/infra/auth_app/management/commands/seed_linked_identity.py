#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed a human's linked identity without waiting for them to log in.

Why this exists: the board can only attribute a card to a human it has a
record for, and until now the cards user tables held no real people at all.
The login path fills them going forward, but the operator's own identity is
needed BEFORE that — his cards already exist and currently attribute to a
bare string.

Usage::

    manage.py seed_linked_identity --username ywatanabe \\
        --email ywata1989@gmail.com --dry-run
    manage.py seed_linked_identity --username ywatanabe \\
        --email ywata1989@gmail.com --email second@example.org

Every address passed here is treated as VERIFIED, because an operator typing
it at a shell IS the verification — there is no provider in the loop. That is
also why this is a management command and not an HTTP endpoint: the trust
comes from shell access, which no web request has.

Idempotent. Re-running adds nothing and changes nothing, so it is safe in a
provisioning script.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.infra.auth_app.account_linking.models import (
    LinkedIdentity,
    VerifiedEmail,
)
from apps.infra.auth_app.account_linking.providers import LOCAL_ISSUER
from apps.infra.auth_app.account_linking.registry import upsert_cards_user
from apps.infra.auth_app.account_linking.service import instance_host_at_name
from apps.infra.auth_app.account_linking.verification import normalize_email

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a human's verified emails + cards identity (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Existing Django username to attach the identity to.",
        )
        parser.add_argument(
            "--email",
            action="append",
            default=[],
            dest="emails",
            help=(
                "Verified address. Repeat for several. The FIRST becomes the "
                "cards record's canonical name."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change and write nothing.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        raw_emails = options["emails"]
        dry_run = options["dry_run"]

        if not raw_emails:
            raise CommandError(
                "at least one --email is required; the address IS the "
                "account key, so seeding an identity without one would "
                "create a record nothing can look up"
            )

        emails: list[str] = []
        for raw in raw_emails:
            email = normalize_email(raw)
            if email is None:
                raise CommandError(f"not a usable email address: {raw!r}")
            if email not in emails:
                emails.append(email)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(
                f"no Django user named {username!r}. Create the account "
                f"first (manage.py createsuperuser, or let them sign up), "
                f"then re-run this to attach the identity."
            ) from exc

        # --- report BEFORE writing, so --dry-run and the real run agree ---
        conflicts = list(
            VerifiedEmail.objects.filter(email__in=emails).exclude(user=user)
        )
        if conflicts:
            raise CommandError(
                "refusing to seed: "
                + "; ".join(
                    f"{row.email} is already the account key of user "
                    f"{row.user.get_username()!r}"
                    for row in conflicts
                )
                + ". Resolve the ownership by hand — silently re-pointing an "
                "account key is how one human becomes two accounts."
            )

        new_emails = [
            email
            for email in emails
            if not VerifiedEmail.objects.filter(email=email, user=user).exists()
        ]

        self.stdout.write(f"user            : {username} (pk={user.pk})")
        self.stdout.write(f"instance        : {instance_host_at_name() or '(unset)'}")
        self.stdout.write(f"addresses       : {', '.join(emails)}")
        self.stdout.write(f"new addresses   : {', '.join(new_emails) or '(none)'}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("dry run — nothing written")
            )
            return

        with transaction.atomic():
            for email in emails:
                VerifiedEmail.objects.get_or_create(
                    email=email, defaults={"user": user}
                )

            identity, _created = LinkedIdentity.objects.update_or_create(
                issuer=LOCAL_ISSUER,
                subject=str(user.pk),
                defaults={
                    "user": user,
                    "verified_email": VerifiedEmail.objects.get(
                        email=emails[0]
                    ),
                    "host_at_name": instance_host_at_name(),
                },
            )

        result = upsert_cards_user(
            email=emails[0],
            display_name=username,
            host_at_name=instance_host_at_name(),
        )
        if result.cards_user_id:
            identity.cards_user_id = result.cards_user_id
            identity.save(update_fields=["cards_user_id"])

        # Any additional addresses become aliases of the same cards user, so
        # a card owned under either address resolves to one human.
        for email in emails[1:]:
            extra = upsert_cards_user(
                email=email,
                display_name=username,
                host_at_name=instance_host_at_name(),
            )
            self.stdout.write(f"  cards alias {email}: {extra.status}")

        style = (
            self.style.SUCCESS if result.cards_user_id else self.style.WARNING
        )
        self.stdout.write(
            style(
                f"cards upsert    : {result.status} "
                f"({result.cards_user_id or 'no id'}) — {result.detail}"
            )
        )
        if not result.cards_user_id:
            self.stdout.write(
                self.style.WARNING(
                    "The hub-side identity IS saved; only the board mirror "
                    "failed. Re-run this command once the cards store is "
                    "reachable — it is idempotent."
                )
            )


# EOF
