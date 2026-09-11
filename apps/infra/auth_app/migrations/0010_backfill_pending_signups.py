"""Backfill PendingSignup for EXISTING pending signups.

WHY THIS EXISTS (PR #775 review). ``0008_pendingsignup`` only CREATED the table.
The marker is what makes an account "a signup awaiting verification", so every
pending signup that already existed before this branch was left with NO marker —
and the classifier treats a row without one as ``INACTIVE_NOT_PENDING``. Those
users could no longer resume or verify. The table without this backfill is a
guarantee applied only to accounts created after the deploy.

THE PREDICATE IS DELIBERATELY STRICT
``is_active=False`` alone is NOT evidence of a signup: an admin-disabled account
is inactive too. Marking every inactive user would hand suspended accounts the
signup authority this branch exists to withhold. So a row is backfilled ONLY if
ALL of these hold, and anything else is LEFT UNTOUCHED and reported:

  * ``is_active=False``
  * a USABLE password — an unusable one (``!``-prefixed) is a deliberately
    locked account, not a signup in progress
  * ``last_login IS NULL`` — they have never signed in
  * NO verified EmailVerification anywhere in their history
  * an UNVERIFIED EmailVerification for the SAME normalized address as the
    account's own

Each clause removes a class of account that is not a pending signup. The
predicate lives in :func:`selection` so the tests exercise THIS logic against the
real models rather than a paraphrase of it.

The command ``audit_legacy_pending_signups`` reports the same selection and the
ambiguity it leaves behind, read-only, if you want to see it before migrating.
"""

from django.conf import settings
from django.db import migrations
from django.db.models import Exists, OuterRef
from django.db.models.functions import Lower


def selection(User, EmailVerification):
    """The EXACT rows that may be backfilled. See the module docstring."""
    matching_unverified = (
        EmailVerification.objects.filter(user=OuterRef("pk"), is_verified=False)
        .annotate(lowered=Lower("email"))
        .filter(lowered=Lower(OuterRef("email")))
    )
    verified_history = EmailVerification.objects.filter(
        user=OuterRef("pk"), is_verified=True
    )
    return (
        User.objects.filter(is_active=False, last_login__isnull=True)
        .exclude(password="")
        .exclude(password__startswith="!")
        .annotate(
            has_matching_unverified=Exists(matching_unverified),
            has_verified=Exists(verified_history),
        )
        .filter(has_matching_unverified=True, has_verified=False)
    )


def backfill(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    PendingSignup = apps.get_model("auth_app", "PendingSignup")
    EmailVerification = apps.get_model("auth_app", "EmailVerification")

    already = set(PendingSignup.objects.values_list("user_id", flat=True))
    candidates = selection(User, EmailVerification).exclude(pk__in=already)

    backfilled = 0
    for user in candidates.iterator():
        PendingSignup.objects.create(user_id=user.pk, email=user.email)
        backfilled += 1

    # REPORT what was deliberately NOT touched, so an operator can see the
    # ambiguity rather than discover it as a stuck account later.
    inactive = User.objects.filter(is_active=False)
    untouched = inactive.exclude(
        pk__in=list(selection(User, EmailVerification).values_list("pk", flat=True))
    )
    print(
        f"\n[backfill_pending_signups] backfilled {backfilled} pending signup(s); "
        f"left {untouched.count()} inactive account(s) UNTOUCHED (no strict "
        f"evidence — admin-disabled, locked, previously signed in, already "
        f"verified, or an address mismatch). Untouched accounts keep NO marker "
        f"and therefore NO signup authority."
    )


def unbackfill(apps, schema_editor):
    """Reverse: drop the markers this migration created.

    Only the rows it could have created are removed, so a marker created later by
    a real signup is not silently revoked by a rollback.
    """
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    PendingSignup = apps.get_model("auth_app", "PendingSignup")
    EmailVerification = apps.get_model("auth_app", "EmailVerification")
    candidate_ids = list(
        selection(User, EmailVerification).values_list("pk", flat=True)
    )
    PendingSignup.objects.filter(user_id__in=candidate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth_app", "0009_identity_case_insensitive_uniqueness"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
