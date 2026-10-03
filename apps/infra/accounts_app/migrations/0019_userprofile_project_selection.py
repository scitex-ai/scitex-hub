from django.db import migrations, models


def seed_existing_project_choices(apps, schema_editor):
    """A valid old FK is an explicit project choice; null never becomes All."""
    Profile = apps.get_model("accounts_app", "UserProfile")
    Project = apps.get_model("project_app", "Project")
    alias = schema_editor.connection.alias
    profiles = Profile.objects.using(alias).exclude(last_active_repository_id=None)
    for profile in profiles.iterator():
        project = (
            Project.objects.using(alias)
            .select_related("owner")
            .filter(pk=profile.last_active_repository_id)
            .first()
        )
        if project is not None and project.owner_id is not None and (
            project.owner_id == profile.user_id
            or project.collaborators.using(alias).filter(pk=profile.user_id).exists()
        ):
            profile.project_selection = {
                "scope": "project",
                "id": f"{project.owner.username}/{project.slug}",
            }
        else:
            profile.last_active_repository_id = None
        profile.save(
            using=alias, update_fields=["project_selection", "last_active_repository"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts_app", "0018_userprofile_keymap_preferences"),
        ("project_app", "0004_alter_project_collaborators"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="project_selection",
            field=models.JSONField(
                blank=True,
                default=None,
                null=True,
                help_text="Explicit user/project selection; null means no selection",
            ),
        ),
        migrations.RunPython(seed_existing_project_choices, migrations.RunPython.noop),
    ]
