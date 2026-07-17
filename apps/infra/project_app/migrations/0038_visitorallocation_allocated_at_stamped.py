"""allocated_at: auto_now_add -> default=timezone.now.

Slot rows are created once and reused across visitors, so auto_now_add
(which fires only on INSERT and ignores assigned values) recorded row
creation, never the current allocation — on prod every row still read
February. The allocator now stamps it explicitly on every handoff, which
auto_now_add would silently discard.
"""

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("project_app", "0037_visitorallocation_quarantine"),
    ]

    operations = [
        migrations.AlterField(
            model_name="visitorallocation",
            name="allocated_at",
            field=models.DateTimeField(default=timezone.now),
        ),
    ]
