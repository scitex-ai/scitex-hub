"""PendingSignup PROVENANCE — and NO data migration, deliberately.

AN EARLIER VERSION OF THIS BRANCH AUTO-BACKFILLED MARKERS and that has been
REMOVED as unsafe. The review's objection is correct: the "strict evidence"
predicate cannot distinguish an abandoned signup from an ADMIN-DISABLED account
that never signed in and happens to carry an old matching unverified row. Applying
it automatically would GRANT SIGNUP AUTHORITY TO A SUSPENDED ACCOUNT — precisely
what this branch exists to prevent. Inference is not evidence.

What replaced it:
  * ``audit_legacy_pending_signups``   — READ-ONLY. Lists candidate user IDs and
    the ambiguous inactive accounts, WITH their evidence. Decides nothing.
  * ``reconcile_legacy_pending_signups`` — takes EXPLICIT user IDs, rechecks the
    evidence transactionally, and records a marker with provenance.

So the decision is a recorded human act, not a heuristic:

    reconciled_at / reconciled_by — set ONLY on an operator-reconciled marker.
    NULL means the marker came from a real signup.

REVERSE IS DELIBERATELY ROW-FREE. The previous reverse recomputed the selection
and deleted those markers, which would have deleted markers created by GENUINE
signups after this migration ran. Dropping two columns cannot do that. A rollback
must never recompute a predicate against rows it did not create.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth_app", "0009_identity_case_insensitive_uniqueness"),
    ]

    operations = [
        migrations.AddField(
            model_name="pendingsignup",
            name="reconciled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pendingsignup",
            name="reconciled_by",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
