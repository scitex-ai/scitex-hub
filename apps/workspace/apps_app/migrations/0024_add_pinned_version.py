"""Add MarketplaceModule.pinned_version: the certified version the badge binds to."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("apps_app", "0023_remove_stale_todo_module")]

    operations = [
        migrations.AddField(
            model_name="appsmodule",
            name="pinned_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Version string certified with the pin (set on "
                "submission; the Verified badge is bound to it — a different "
                "version shows no badge in production until re-certified)",
                max_length=20,
            ),
        ),
    ]
