from django.db import migrations


class Migration(migrations.Migration):
    """Rename Python model classes: UserModule→UserApp, ModuleExecution→AppExecution.

    db_table is explicit on both models so no DB tables are altered.
    This is a Python-only rename tracked in django_migrations.
    """

    dependencies = [
        ("appmaker_app", "0003_rename_app_label"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="UserModule",
            new_name="UserApp",
        ),
        migrations.RenameModel(
            old_name="ModuleExecution",
            new_name="AppExecution",
        ),
    ]
