"""
Management command to set up social authentication providers.

Usage:
    python manage.py setup_social_auth

This command creates the necessary Site and SocialApp entries
for Google and ORCID OAuth providers.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Set up social authentication providers (Google, ORCID)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default="127.0.0.1:8000",
            help="Site domain (e.g., scitex.ai or 127.0.0.1:8000)",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="SciTeX",
            help="Site name",
        )

    def handle(self, *args, **options):
        domain = options["domain"]
        name = options["name"]

        self.stdout.write(self.style.NOTICE("Setting up social authentication..."))

        # Step 1: Configure the Site
        self.stdout.write(f"\n1. Configuring Site (domain: {domain})...")
        try:
            site, created = Site.objects.update_or_create(
                id=settings.SITE_ID,
                defaults={
                    "domain": domain,
                    "name": name,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"   Created Site: {site}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"   Updated Site: {site}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   Error configuring Site: {e}"))
            return

        # Step 2: Check for social auth credentials
        self.stdout.write("\n2. Checking OAuth credentials...")

        google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        google_client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
        orcid_client_id = getattr(settings, "ORCID_CLIENT_ID", "")
        orcid_client_secret = getattr(settings, "ORCID_CLIENT_SECRET", "")

        # Step 3: Create SocialApp entries
        self.stdout.write("\n3. Configuring OAuth providers...")

        try:
            from allauth.socialaccount.models import SocialApp

            # Google
            if google_client_id and google_client_secret:
                google_app, created = SocialApp.objects.update_or_create(
                    provider="google",
                    defaults={
                        "name": "Google",
                        "client_id": google_client_id,
                        "secret": google_client_secret,
                    },
                )
                google_app.sites.add(site)
                status = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"   {status} Google OAuth app"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "   Skipped Google (SCITEX_GOOGLE_CLIENT_ID/SECRET not set)"
                    )
                )

            # ORCID
            if orcid_client_id and orcid_client_secret:
                orcid_app, created = SocialApp.objects.update_or_create(
                    provider="orcid",
                    defaults={
                        "name": "ORCID",
                        "client_id": orcid_client_id,
                        "secret": orcid_client_secret,
                    },
                )
                orcid_app.sites.add(site)
                status = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"   {status} ORCID OAuth app"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "   Skipped ORCID (ORCID_CLIENT_ID/SECRET not set)"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   Error configuring providers: {e}"))
            self.stdout.write(
                self.style.NOTICE(
                    "\n   You may need to run migrations first:\n"
                    "   python manage.py migrate"
                )
            )
            return

        # Step 4: Print summary and next steps
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("Social authentication setup complete!"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Get OAuth credentials from providers:")
        self.stdout.write("   - Google: https://console.cloud.google.com/apis/credentials")
        self.stdout.write("   - ORCID: https://orcid.org/developer-tools")
        self.stdout.write("\n2. Set environment variables:")
        self.stdout.write("   - SCITEX_GOOGLE_CLIENT_ID")
        self.stdout.write("   - SCITEX_GOOGLE_CLIENT_SECRET")
        self.stdout.write("   - ORCID_CLIENT_ID")
        self.stdout.write("   - ORCID_CLIENT_SECRET")
        self.stdout.write(f"\n3. Add redirect URIs in provider consoles:")
        self.stdout.write(f"   - Google: https://{domain}/auth/social/google/login/callback/")
        self.stdout.write(f"   - ORCID: https://{domain}/auth/social/orcid/login/callback/")
        self.stdout.write("\n4. Re-run this command after setting credentials")
