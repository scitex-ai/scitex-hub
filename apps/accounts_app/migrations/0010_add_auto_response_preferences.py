from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0009_add_mcp_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="auto_response_preferences",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Auto-response config: {y_n, y_y_n, waiting, suggestion}",
            ),
        ),
    ]
