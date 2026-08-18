# -*- coding: utf-8 -*-
# File: apps/infra/auth_app/management/commands/sync_site_domain.py
"""Make the django.contrib.sites row match this deployment, from configuration.

WHY THIS EXISTS. Production ran for an unknown length of time with its single
Site row set to ``127.0.0.1:8000``. Nothing detected it, because every check
anyone ran reported success: the OAuth env vars were set, the SocialApp rows
existed with credentials, and ``setup_social_auth`` had evidently been run.
The one value nobody looked at was the domain those things hang off.

It got there the documented way. ``setup_social_auth``'s own usage line is
``python manage.py setup_social_auth`` with no flags, and its ``--domain``
default was the literal string ``127.0.0.1:8000`` -- so the INVITED invocation
stamped a development value onto whatever database it was pointed at.

WHAT THE WRONG DOMAIN BREAKS. It is not cosmetic. ``SITE_ID`` pins allauth and
Django to this row, so the value is the domain the framework hands out:

  * allauth resolves a ``SocialApp`` through the current Site, so OAuth
    callbacks are built against it -- a provider cannot round-trip to a host
    called ``127.0.0.1``;
  * allauth builds email confirmation and password-reset links from
    ``get_current_site``, so every such message carries a link pointing at the
    recipient's own machine;
  * ``setup_social_auth`` prints the redirect URIs an operator must register in
    the Google and ORCID consoles FROM THIS ROW, so a wrong value does not just
    break the site, it hands a human the wrong thing to paste into a console.

SO IT IS CONFIGURATION, NOT DATA. The domain differs per environment exactly
like a database URL differs per environment, and the fleet keeps that kind of
difference in the env file rather than in database state. Operator ruling,
2026-08-18, choosing this over editing the row by hand -- hand-editing is how it
reached the broken state, and a hand-edited row drifts back the next time
someone runs the setup command.

ONE SOURCE, NOT TWO. hub already configures its public address as
``SCITEX_HUB_SITE_URL``, and production already sets it to ``https://scitex.ai``.
The Site domain is the HOST PART of that, derived -- not a second variable that
can disagree with it. The configuration was already correct; nothing applied it.

IT REFUSES RATHER THAN GUESSING. With ``SCITEX_HUB_SITE_URL`` unset this command
fails loudly and names it. ``SITE_URL`` itself falls back to
``http://127.0.0.1:8000`` for local development, and deriving the Site domain
from that fallback is precisely how production came to hold a localhost value --
so an unset URL yields an empty domain and a refusal, never a guess.

Idempotent: run it on every boot. It reports whether it changed anything.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Set the django.contrib.sites row for this deployment from "
        "$SCITEX_HUB_SITE_DOMAIN. Idempotent; safe to run on every boot."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help=(
                "Report whether the stored domain already matches the "
                "configured one, and exit non-zero if it does not. Changes "
                "nothing."
            ),
        )

    def handle(self, *args, **options):
        configured = (getattr(settings, "SITE_DOMAIN", "") or "").strip()
        if not configured:
            raise CommandError(
                "SCITEX_HUB_SITE_URL is not set, so there is no domain to "
                "apply and this command will not invent one.\n"
                "  Set it in the env file this deployment loads, e.g.\n"
                "    SCITEX_HUB_SITE_URL=https://scitex.ai        (production)\n"
                "    SCITEX_HUB_SITE_URL=http://127.0.0.1:8000    (local dev)\n"
                "  The Site domain is DERIVED from it (its host part) by\n"
                "  config/settings/settings_auth.py, so there is exactly one\n"
                "  place to set this deployment's address. It is the domain\n"
                "  allauth uses for OAuth callbacks and for the links in\n"
                "  confirmation and password-reset email."
            )

        name = (getattr(settings, "SITE_NAME", "") or "SciTeX").strip()
        site_id = settings.SITE_ID

        try:
            site = Site.objects.filter(id=site_id).first()
        except Exception as exc:  # database not reachable / not migrated yet
            raise CommandError(
                f"could not read Site id={site_id}: {exc}\n"
                "  If this ran before migrations, move it after `migrate`."
            ) from exc

        previous = site.domain if site else None

        if previous == configured and site and site.name == name:
            self.stdout.write(f"Site id={site_id} already {configured!r}; unchanged.")
            return

        if options["check"]:
            raise CommandError(
                f"Site id={site_id} is {previous!r}, expected {configured!r}. "
                "Run `python manage.py sync_site_domain` to fix it."
            )

        Site.objects.update_or_create(
            id=site_id,
            defaults={"domain": configured, "name": name},
        )
        # Django caches the current Site per process; a stale cache would make
        # the very request that triggered a fix still emit the old domain.
        Site.objects.clear_cache()

        if previous is None:
            self.stdout.write(self.style.SUCCESS(f"Site id={site_id} created as {configured!r}."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Site id={site_id} updated: {previous!r} -> {configured!r}."
                )
            )
