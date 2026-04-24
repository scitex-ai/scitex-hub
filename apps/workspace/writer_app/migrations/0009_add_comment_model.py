"""No-op: Comment model and its indexes are already created by 0008.

Historically this migration attempted ``CreateModel(name="Comment", ...)``
plus three ``AddIndex`` operations, but migration 0008 was later amended to
also create the Comment model (with ``BigAutoField`` id and its indexes).
Applying 0009 on top of 0008 therefore raised::

    django.db.utils.ProgrammingError:
        relation "writer_app_comment" already exists

Keeping this migration as an empty graph node preserves the dependency chain
used by 0010_add_comment_anchor_fields.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "writer_app",
            "0008_manuscript_collaborators_collaborationinvitation_and_more",
        ),
    ]

    operations = []
