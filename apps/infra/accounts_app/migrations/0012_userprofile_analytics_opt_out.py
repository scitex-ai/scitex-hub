from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts_app", "0011_userprofile_apptainer_container_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="analytics_opt_out",
            field=models.BooleanField(
                default=False,
                help_text="Opt out of anonymized usage analytics (Umami)",
            ),
        ),
    ]
