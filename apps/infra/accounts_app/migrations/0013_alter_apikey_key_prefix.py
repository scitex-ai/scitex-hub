from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0012_userprofile_analytics_opt_out"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apikey",
            name="key_prefix",
            field=models.CharField(
                help_text="First 15 characters of the key (for display)",
                max_length=15,
                unique=True,
            ),
        ),
    ]
