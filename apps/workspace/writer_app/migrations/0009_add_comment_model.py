"""Add Comment model for manuscript review annotations."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "writer_app",
            "0008_manuscript_collaborators_collaborationinvitation_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Comment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "section_id",
                    models.CharField(
                        help_text="Which .tex section this comment targets (e.g. 'manuscript/methods')",
                        max_length=200,
                    ),
                ),
                (
                    "line_start",
                    models.IntegerField(
                        help_text="Starting line number in the section",
                    ),
                ),
                (
                    "line_end",
                    models.IntegerField(
                        help_text="Ending line number in the section",
                    ),
                ),
                (
                    "text",
                    models.TextField(
                        help_text="Comment content",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("resolved", "Resolved"),
                            ("closed", "Closed"),
                        ],
                        default="open",
                        help_text="Current status of this comment thread",
                        max_length=10,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "author",
                    models.ForeignKey(
                        help_text="User who wrote this comment",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="writer_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "manuscript",
                    models.ForeignKey(
                        help_text="Manuscript this comment belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="writer_app.manuscript",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent comment for reply threads (null for top-level comments)",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="writer_app.comment",
                    ),
                ),
            ],
            options={
                "ordering": ["section_id", "line_start", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["manuscript", "section_id"],
                name="writer_app__manuscr_b1c2d3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["manuscript", "status"],
                name="writer_app__manuscr_e4f5a6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["parent"],
                name="writer_app__parent__7b8c9d_idx",
            ),
        ),
    ]
