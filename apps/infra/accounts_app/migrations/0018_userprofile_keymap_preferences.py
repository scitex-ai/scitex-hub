from django.db import migrations, models

import apps.infra.accounts_app.keymap_preferences


class Migration(migrations.Migration):

    dependencies = [
        ("accounts_app", "0017_userprofile_public_id_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="keymap_preferences",
            field=models.JSONField(
                blank=True,
                default=apps.infra.accounts_app.keymap_preferences.empty_preferences,
                help_text=(
                    "Versioned per-user global and app-mode keyboard shortcut overrides"
                ),
            ),
        ),
    ]
