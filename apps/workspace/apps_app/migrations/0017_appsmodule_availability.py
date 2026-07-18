# Hand-written 2026-07-18 — AppsModule.availability (launcher tile state).
# Operator directive (Telegram 1483): communicate availability AT the home
# icon — unfinished apps badge "Coming Soon" and never navigate; the state
# is a catalog/registry FIELD, never hardcoded in templates (card
# hub-launcher-tile-availability-states).
#
# The data step marks the two unfinished apps the operator named — Live
# Paper and Agentic Journal — coming_soon. Their store rows were published
# from repo slugs (dash and underscore variants both exist in the wild:
# "scitex-live-paper-app", "scitex_agentic_journal_hub_app", ...), so the
# match normalises underscores to dashes and substring-matches the two app
# identities. No other row is touched.

from django.db import migrations, models

# The two unfinished apps, by normalised identity substring.
_COMING_SOON_IDENTITIES = ("live-paper", "agentic-journal")


def _mark_unfinished_coming_soon(apps, schema_editor):
    AppsModule = apps.get_model("apps_app", "AppsModule")
    for row in AppsModule.objects.all():
        normalized = row.module_name.replace("_", "-")
        if any(identity in normalized for identity in _COMING_SOON_IDENTITIES):
            row.availability = "coming_soon"
            row.save(update_fields=["availability"])


def _unmark(apps, schema_editor):
    AppsModule = apps.get_model("apps_app", "AppsModule")
    for row in AppsModule.objects.filter(availability="coming_soon"):
        normalized = row.module_name.replace("_", "-")
        if any(identity in normalized for identity in _COMING_SOON_IDENTITIES):
            row.availability = "available"
            row.save(update_fields=["availability"])


class Migration(migrations.Migration):

    dependencies = [
        ("apps_app", "0016_blank_selfnamed_display_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsmodule",
            name="availability",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("coming_soon", "Coming Soon"),
                    ("desktop_only", "Desktop-only"),
                ],
                default="available",
                help_text=(
                    "Launcher-tile state: available, coming_soon (badge, not "
                    "launchable), desktop_only (badge + no launch on mobile)."
                ),
                max_length=15,
            ),
        ),
        migrations.RunPython(_mark_unfinished_coming_soon, _unmark),
    ]
