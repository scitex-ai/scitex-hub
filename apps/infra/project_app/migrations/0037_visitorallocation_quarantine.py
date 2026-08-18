"""Add quarantine state to VisitorAllocation (visitor-slot isolation audit).

Slots that fail the wipe+verify pipeline — or are in an unknown state at
boot — are quarantined and never allocated until re-verified clean.
Also updates the workspace_ready help_text to reflect its hardened
semantics (verified-clean gate instead of async-init progress flag).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0036_visitorallocation_workspace_ready"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitorallocation",
            name="quarantined",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Slot failed wipe/verify (or was in an unknown state at boot) "
                    "and must NEVER be allocated until re-verified clean via "
                    "`manage.py reconcile_visitor_slots`."
                ),
            ),
        ),
        migrations.AddField(
            model_name="visitorallocation",
            name="quarantined_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visitorallocation",
            name="quarantine_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="visitorallocation",
            name="workspace_ready",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Whether the slot's workspace has been wiped, re-cloned and "
                    "VERIFIED clean. Allocation only serves slots with "
                    "workspace_ready=True (security gate — see visitor_pool README)."
                ),
            ),
        ),
    ]
