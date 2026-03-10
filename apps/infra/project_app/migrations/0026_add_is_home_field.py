from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0025_add_issue_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_home",
            field=models.BooleanField(
                default=False,
                help_text="Home project: persistent, always private, cannot be deleted",
            ),
        ),
    ]
