"""New projects default to private. Existing rows keep their visibility."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0040_default_project_names_the_demo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="visibility",
            field=models.CharField(
                choices=[("public", "Public"), ("private", "Private")],
                default="private",
                help_text="Repository visibility: public (anyone can see) or private (only collaborators)",
                max_length=20,
            ),
        ),
    ]
