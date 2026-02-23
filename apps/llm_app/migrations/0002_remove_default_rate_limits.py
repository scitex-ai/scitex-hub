from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("llm_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconnection",
            name="daily_request_limit",
            field=models.IntegerField(
                null=True,
                blank=True,
                default=None,
                help_text="Maximum requests per day (empty = unlimited)",
            ),
        ),
        migrations.AlterField(
            model_name="llmconnection",
            name="daily_token_limit",
            field=models.IntegerField(
                null=True,
                blank=True,
                default=None,
                help_text="Maximum tokens per day (empty = unlimited)",
            ),
        ),
    ]
