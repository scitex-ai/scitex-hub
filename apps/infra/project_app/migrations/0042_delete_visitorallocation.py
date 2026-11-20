from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0041_project_visibility_default_private"),
    ]

    operations = [
        # Stop using allocations without deleting retained historical records.
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="VisitorAllocation")],
        ),
    ]
