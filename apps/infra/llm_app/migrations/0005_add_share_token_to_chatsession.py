"""Add share_token (UUID) and is_shared (bool) to ChatSession."""

import uuid

from django.db import migrations, models


def backfill_share_tokens(apps, schema_editor):
    """Assign UUIDs to existing sessions that have NULL share_token."""
    ChatSession = apps.get_model("llm_app", "ChatSession")
    for session in ChatSession.objects.filter(share_token__isnull=True):
        session.share_token = uuid.uuid4()
        session.save(update_fields=["share_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("llm_app", "0004_chatsession_chatmessage"),
    ]

    operations = [
        # Step 1: Add fields as nullable first (for backfill)
        migrations.AddField(
            model_name="chatsession",
            name="share_token",
            field=models.UUIDField(
                null=True,
                help_text="Public share token (URL key for read-only access)",
            ),
        ),
        migrations.AddField(
            model_name="chatsession",
            name="is_shared",
            field=models.BooleanField(
                default=False,
                help_text="Whether the session is publicly accessible via share_token",
            ),
        ),
        # Step 2: Backfill existing rows
        migrations.RunPython(backfill_share_tokens, migrations.RunPython.noop),
        # Step 3: Make non-nullable with default and add unique index
        migrations.AlterField(
            model_name="chatsession",
            name="share_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                db_index=True,
                help_text="Public share token (URL key for read-only access)",
            ),
        ),
    ]
