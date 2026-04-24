"""Add text-snippet anchor fields to Comment model for position-resilient anchoring."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("writer_app", "0009_add_comment_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="anchor_text",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Verbatim text snippet this comment is anchored to (for re-matching after edits)",
            ),
        ),
        migrations.AddField(
            model_name="comment",
            name="anchor_context_before",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                help_text="~50 chars of text before the anchor (disambiguation)",
            ),
        ),
        migrations.AddField(
            model_name="comment",
            name="anchor_context_after",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                help_text="~50 chars of text after the anchor (disambiguation)",
            ),
        ),
    ]
