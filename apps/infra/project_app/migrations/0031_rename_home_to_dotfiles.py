"""Rename home projects to dotfiles projects.

The 'home' project (is_home=True) is replaced by a 'dotfiles' project
that maps to ~/proj/dotfiles/ instead of ~/proj/home -> .. symlink.
"""

from django.db import migrations


def rename_home_to_dotfiles(apps, schema_editor):
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(is_home=True, slug="home").update(
        name="dotfiles",
        slug="dotfiles",
    )


def rename_dotfiles_to_home(apps, schema_editor):
    Project = apps.get_model("project_app", "Project")
    Project.objects.filter(is_home=True, slug="dotfiles").update(
        name="home",
        slug="home",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0030_project_topics"),
    ]

    operations = [
        migrations.RunPython(
            rename_home_to_dotfiles,
            reverse_code=rename_dotfiles_to_home,
        ),
    ]
