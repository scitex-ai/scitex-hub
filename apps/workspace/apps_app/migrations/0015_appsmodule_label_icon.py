# Hand-written 2026-07-18 — AppsModule display metadata (label + icon).
# Store-published apps rendered as raw package slugs with a generic
# puzzle-piece icon because the catalog had nowhere to store the
# manifest's display metadata (card hub-appsmodule-missing-label-icon).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps_app', '0014_alter_appsmodule_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsmodule',
            name='label',
            field=models.CharField(blank=True, help_text="Human-readable display name (manifest.json 'label')", max_length=100),
        ),
        migrations.AddField(
            model_name='appsmodule',
            name='icon',
            field=models.CharField(blank=True, help_text="FontAwesome class string (manifest.json 'icon')", max_length=100),
        ),
    ]
