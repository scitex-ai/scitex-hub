"""App Store copy unification (help_text only, no schema change)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0042_delete_visitorallocation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="app_category",
            field=models.CharField(
                blank=True,
                default="",
                help_text="App category for App Store listing",
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="app_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("under_review", "Under Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                help_text="App Store submission status",
                max_length=20,
                null=True,
            ),
        ),
    ]
