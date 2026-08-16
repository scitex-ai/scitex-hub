# -*- coding: utf-8 -*-
# File: apps/infra/accounts_app/migrations/0014_visitors_land_on_the_demo_project.py
"""Repoint visitor profiles from the dotfiles home project to the demo project.

The signal fix in ``accounts_app/signals.py`` prevents this for profiles that
have no landing project yet. It cannot help the sixteen visitor slots already
provisioned: their ``last_active_repository`` is already set — to the wrong
project — so nothing in the login path revisits it.

MEASURED ON PRODUCTION, 2026-08-16. Every visitor workspace holds both
projects on disk:

    proj/default-project/   figures/confusion_matrix.png, figures/digit_grid.png,
                            data/digits_sample.csv, scripts/reproduce_figures.py
    proj/dotfiles/          install.sh, bash_profile, screenrc, gitconfig

Loaded as an anonymous visitor, /apps/writer/ rendered "dotfiles · Writer",
0 words and a blank manuscript, while the seeded demo sat unopened beside it.
The content was never missing; the pointer was wrong.

SCOPED TO VISITOR ACCOUNTS ON PURPOSE. ``last_active_repository`` means "where
this user was last working" and it moves as a human navigates, so rewriting it
for a real account would overwrite a choice somebody made. A visitor slot that
still points at its home project has, by definition, never navigated anywhere.
Restricting to ``username__startswith="visitor-"`` keeps the blast radius to
exactly the rows this is about.

Reversible: the reverse puts each affected profile back on its home project.
"""

from django.db import migrations

VISITOR_USERNAME_PREFIX = "visitor-"


def land_visitors_on_the_demo(apps, schema_editor):
    """Move visitor profiles off the home project, where a demo exists."""
    UserProfile = apps.get_model("accounts_app", "UserProfile")
    Project = apps.get_model("project_app", "Project")

    profiles = UserProfile.objects.filter(
        user__username__startswith=VISITOR_USERNAME_PREFIX,
        last_active_repository__is_home=True,
    ).select_related("user", "last_active_repository")

    for profile in profiles:
        demo = (
            Project.objects.filter(owner=profile.user, is_home=False)
            .order_by("id")
            .first()
        )
        # No non-home project means there is nothing better to point at, and
        # leaving the profile alone is preferable to pointing it at nothing.
        if demo is None:
            continue
        profile.last_active_repository = demo
        profile.save(update_fields=["last_active_repository"])


def land_visitors_on_the_home_project(apps, schema_editor):
    """Reverse: put visitor profiles back on their home project."""
    UserProfile = apps.get_model("accounts_app", "UserProfile")
    Project = apps.get_model("project_app", "Project")

    profiles = UserProfile.objects.filter(
        user__username__startswith=VISITOR_USERNAME_PREFIX,
        last_active_repository__is_home=False,
    ).select_related("user")

    for profile in profiles:
        home = Project.objects.filter(owner=profile.user, is_home=True).first()
        if home is None:
            continue
        profile.last_active_repository = home
        profile.save(update_fields=["last_active_repository"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0013_alter_apikey_key_prefix"),
        ("project_app", "0040_default_project_names_the_demo"),
    ]

    operations = [
        migrations.RunPython(
            land_visitors_on_the_demo, land_visitors_on_the_home_project
        ),
    ]


# EOF
