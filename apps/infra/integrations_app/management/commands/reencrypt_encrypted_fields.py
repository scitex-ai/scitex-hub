"""Re-encrypt every stored field secret with the newest field-encryption key.

Every model that declares ``ENCRYPTED_FIELDS`` is covered. Each non-empty value
is classified (see ``apps.field_encryption.key_state``):

- current:     already readable with the newest key; left untouched
- stale:       readable only with an older/legacy key; re-encrypted
- unreadable:  no accepted key reads it; left untouched and reported

Idempotent: a second run finds everything ``current``. Only counts are printed,
never values. ``--check`` writes nothing and exits non-zero unless every value
is current, which is how a rotation is verified before the old key is dropped.

Run as the application user, not root (shared log volume).
"""

from collections import Counter

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps import field_encryption


def encrypted_models():
    """Models declaring ``ENCRYPTED_FIELDS``, in a stable order."""
    found = [
        m for m in django_apps.get_models() if getattr(m, "ENCRYPTED_FIELDS", None)
    ]
    return sorted(found, key=lambda m: m._meta.label)


class Command(BaseCommand):
    help = "Re-encrypt stored field secrets with the newest SCITEX_HUB_FIELD_ENCRYPTION_KEYS key."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Write nothing; exit non-zero unless every stored value is current.",
        )

    def handle(self, *args, check=False, **options):
        if not field_encryption.configured_keys():
            raise CommandError(
                f"{field_encryption.ENV_NAME} is not set: there is no field key to "
                "re-encrypt to. Add one (newest first) and recreate the services."
            )

        totals = Counter()
        for model in encrypted_models():
            fields = tuple(model.ENCRYPTED_FIELDS)
            counts = {f: Counter() for f in fields}
            with transaction.atomic():
                rows = model.objects.select_for_update().only("pk", *fields)
                for row in rows.iterator():
                    updates = {}
                    for field in fields:
                        token = getattr(row, field)
                        if not token:
                            counts[field]["empty"] += 1
                            continue
                        state = field_encryption.key_state(token)
                        if state == field_encryption.STALE and not check:
                            updates[field] = field_encryption.reencrypt(token)
                            counts[field]["reencrypted"] += 1
                        else:
                            counts[field][state] += 1
                    if updates:
                        # queryset.update: no save() signals, no auto_now bump.
                        model.objects.filter(pk=row.pk).update(**updates)
            for field in fields:
                c = counts[field]
                totals.update(c)
                self.stdout.write(
                    f"{model._meta.label}.{field}: current={c['current']} "
                    f"reencrypted={c['reencrypted']} stale={c['stale']} "
                    f"unreadable={c['unreadable']} empty={c['empty']}"
                )

        self.stdout.write(
            f"TOTAL: current={totals['current']} reencrypted={totals['reencrypted']} "
            f"stale={totals['stale']} unreadable={totals['unreadable']}"
        )
        if totals["unreadable"]:
            raise CommandError(
                f"{totals['unreadable']} stored value(s) are unreadable with every "
                "accepted key; they were left untouched."
            )
        if check and totals["stale"]:
            raise CommandError(
                f"{totals['stale']} stored value(s) still need re-encryption."
            )
