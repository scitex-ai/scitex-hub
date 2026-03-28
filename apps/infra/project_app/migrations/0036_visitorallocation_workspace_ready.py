"""Add workspace_ready field to VisitorAllocation for async workspace init."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0035_convert_trip_to_remote"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitorallocation",
            name="workspace_ready",
            field=models.BooleanField(
                default=False,
                help_text="Whether async workspace initialization (template clone) has completed",
            ),
        ),
    ]
