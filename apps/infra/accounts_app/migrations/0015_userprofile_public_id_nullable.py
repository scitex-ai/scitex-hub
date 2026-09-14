# -*- coding: utf-8 -*-
# File: apps/infra/accounts_app/migrations/0015_userprofile_public_id_nullable.py
"""Step 1/3 of adding ``UserProfile.public_id`` (the opaque id ``GET /api/me/`` returns).

Added NULLABLE with no default on purpose. ``AddField(default=uuid.uuid4)``
evaluates the callable ONCE and writes that single value into every existing
row, so a unique constraint would fail (or, without one, every pre-existing
user would share one "unique" id). The standard three-step instead:

1. this migration   — add the column nullable, no default;
2. 0016             — RunPython backfills a distinct ``uuid4`` per row;
3. 0017             — alter to ``unique=True``, non-null, ``default=uuid.uuid4``.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0014_visitors_land_on_the_demo_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
    ]


# EOF
