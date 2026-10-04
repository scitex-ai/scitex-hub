"""Retire the unused model state while preserving its historical table and data."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("scholar_app", "0019_savedgraph")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="SearchFilter")],
        )
    ]
