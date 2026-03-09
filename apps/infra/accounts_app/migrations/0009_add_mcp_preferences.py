from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0008_add_unix_uid_to_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="mcp_preferences",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="MCP tool group toggles: {GROUP_NAME: bool}",
            ),
        ),
    ]
