# -*- coding: utf-8 -*-
# File: apps/infra/accounts_app/migrations/0017_userprofile_public_id_unique.py
"""Step 3/3: ``public_id`` becomes unique, non-null, defaulting to ``uuid4``.

Every row was backfilled with a distinct value by 0016, so the NOT NULL and
UNIQUE constraints apply cleanly. New profiles get their id from the model
default at creation time.
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0016_userprofile_public_id_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                help_text=(
                    "Stable, immutable, never-reused opaque user id exposed by "
                    "GET /api/me/. Never derived from User.pk."
                ),
            ),
        ),
    ]


# EOF
