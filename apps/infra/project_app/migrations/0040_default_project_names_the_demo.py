"""Re-backfill the visitor default project's name now that it HAS content.

0039 renamed 67 prod rows off the slug and onto ``"My Project"``, which was
honest while a visitor's workspace was a placeholder skeleton: there was
nothing to name it after. ``demo_seed`` now lays a worked example on top of
the clone, so the switcher can say WHAT the project is — and, just as
importantly, that it is an EXAMPLE. "My Project" is the same kind of label the
operator objected to in "dotfiles": true, and meaningless to a stranger.

Without this migration the rename would reach only slots that get RECYCLED
after deploy; every already-provisioned row would keep the old name
indefinitely, so the board and the switcher would disagree with the manuscript
the visitor is reading.

Scope, unchanged from 0039: ``name`` ONLY. The slug is load-bearing
infrastructure — pool_manager, pool_cleanup, home_state's recycled-home gate,
the console terminal consumer and the Gitea repo path
``visitor-NNN/default-project`` all query or build it — so it is never written
here.

Idempotent, and narrow on purpose: the forward pass matches only rows still
carrying 0039's exact literal, so a second run matches nothing and a visitor
who renamed their project keeps their name. Reverse restores 0039's value for
exactly the rows this migration renamed.
"""

from django.db import migrations

# FROZEN SNAPSHOT. A migration must not import application code — its
# behaviour has to stay fixed as the code moves on — so these literals are
# duplicated on purpose. The LIVE authority is
# WorkspaceManager.DEFAULT_PROJECT_SLUG / .DEFAULT_PROJECT_DISPLAY_NAME, and
# test_default_project_name_backfill_migration.py pins the NEW literal below
# to that constant so this snapshot cannot silently drift from the code.
# PREVIOUS_DISPLAY_NAME is deliberately NOT pinned to anything live: it is
# 0039's value, frozen forever, and 0039 must never be edited.
DEFAULT_PROJECT_SLUG = "default-project"
PREVIOUS_DISPLAY_NAME = "My Project"
DEFAULT_PROJECT_DISPLAY_NAME = "Handwritten Digits (Example)"


def name_default_projects_for_the_demo(apps, schema_editor):
    """Rename rows still carrying 0039's name. Never writes slug."""
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(
        slug=DEFAULT_PROJECT_SLUG, name=PREVIOUS_DISPLAY_NAME
    ).update(name=DEFAULT_PROJECT_DISPLAY_NAME)


def restore_previous_display_name(apps, schema_editor):
    """Reverse: put 0039's name back for exactly the rows we renamed."""
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(
        slug=DEFAULT_PROJECT_SLUG, name=DEFAULT_PROJECT_DISPLAY_NAME
    ).update(name=PREVIOUS_DISPLAY_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0039_default_project_display_name"),
    ]

    operations = [
        migrations.RunPython(
            name_default_projects_for_the_demo, restore_previous_display_name
        ),
    ]
