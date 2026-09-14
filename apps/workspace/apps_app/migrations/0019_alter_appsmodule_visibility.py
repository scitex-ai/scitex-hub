from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_app", "0018_firstrunprogress"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appsmodule",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("private", "Private"),
                    ("unlisted", "Unlisted"),
                    ("public", "Public"),
                    ("internal", "Internal (staff only)"),
                ],
                default="private",
                max_length=10,
            ),
        ),
    ]
