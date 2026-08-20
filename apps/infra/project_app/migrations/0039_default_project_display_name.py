"""Backfill the visitor default project's human-facing name.

Both visitor-pool creation sites wrote the SLUG into ``name``
(``workspace_manager`` assigned ``name=project_slug``;
``pool_initialization`` hardcoded the same literal), so on prod 67
Project rows carried ``slug == name == "default-project"`` and a
first-time visitor's first noun was that string, in the project
switcher (operator complaint 2026-07-30: 「まずわかりにくい」).

Scope: this migration touches ``name`` ONLY. The slug is load-bearing
infrastructure — pool_manager, pool_cleanup, home_state's recycled-home
gate, the console terminal consumer and the Gitea repo path
``visitor-NNN/default-project`` all query or build it — so it is never
written here.

Idempotent: the forward pass matches only rows still named after their
slug, so a second run matches nothing, and a visitor who renamed their
project keeps their name. Reverse restores the slug as the name for
exactly the rows this migration renamed.
"""

from django.db import migrations

# FROZEN SNAPSHOT of the two values as of this migration. A migration
# must not import application code (its behaviour has to stay fixed even
# as the code moves on), so the literals are duplicated here on purpose.
# The LIVE authority is WorkspaceManager.DEFAULT_PROJECT_SLUG /
# .DEFAULT_PROJECT_DISPLAY_NAME in
# apps/infra/project_app/services/visitor_pool/workspace_manager.py, and
# tests/apps/project_app/services/visitor_pool/
# test_default_project_display_name.py pins these two literals to those
# constants so the snapshot cannot silently drift.
DEFAULT_PROJECT_SLUG = "default-project"
DEFAULT_PROJECT_DISPLAY_NAME = "My Project"


def name_default_projects_for_humans(apps, schema_editor):
    """Rename rows whose ``name`` is still the slug. Never writes slug."""
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(
        slug=DEFAULT_PROJECT_SLUG, name=DEFAULT_PROJECT_SLUG
    ).update(name=DEFAULT_PROJECT_DISPLAY_NAME)


def restore_slug_as_name(apps, schema_editor):
    """Reverse: put the slug back in ``name`` for the rows we renamed."""
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(
        slug=DEFAULT_PROJECT_SLUG, name=DEFAULT_PROJECT_DISPLAY_NAME
    ).update(name=DEFAULT_PROJECT_SLUG)


class Migration(migrations.Migration):

    dependencies = [
        ("project_app", "0038_visitorallocation_allocated_at_stamped"),
    ]

    operations = [
        migrations.RunPython(
            name_default_projects_for_humans, restore_slug_as_name
        ),
    ]
