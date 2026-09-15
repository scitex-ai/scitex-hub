# -*- coding: utf-8 -*-
# File: apps/infra/accounts_app/migrations/0016_userprofile_public_id_backfill.py
"""Step 2/3: give every existing ``UserProfile`` its OWN ``uuid4`` public_id.

One ``uuid.uuid4()`` call per row — never a shared value. Only rows still
NULL are touched, so re-running (or a row created between steps) is safe and
an id, once assigned, is never rewritten: the id is immutable by contract.
The reverse is a no-op; 0015's reverse drops the column.
"""

import uuid

from django.db import migrations

BATCH_SIZE = 500


def backfill_public_ids(apps, schema_editor):
    UserProfile = apps.get_model("accounts_app", "UserProfile")
    pending = []
    for profile in UserProfile.objects.filter(public_id__isnull=True).only("pk").iterator():
        profile.public_id = uuid.uuid4()
        pending.append(profile)
        if len(pending) >= BATCH_SIZE:
            UserProfile.objects.bulk_update(pending, ["public_id"])
            pending = []
    if pending:
        UserProfile.objects.bulk_update(pending, ["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0015_userprofile_public_id_nullable"),
    ]

    operations = [
        migrations.RunPython(backfill_public_ids, migrations.RunPython.noop),
    ]


# EOF
