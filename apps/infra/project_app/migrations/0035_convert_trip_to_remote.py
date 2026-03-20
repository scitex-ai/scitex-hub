"""Convert existing trip projects to remote with connection_mode=trip."""

from django.db import migrations


def convert_trip_to_remote(apps, schema_editor):
    """Migrate trip projects to remote type with trip connection mode."""
    Project = apps.get_model("project_app", "Project")
    TripProjectConfig = apps.get_model("project_app", "TripProjectConfig")
    RemoteProjectConfig = apps.get_model("project_app", "RemoteProjectConfig")

    for trip_config in TripProjectConfig.objects.all():
        project = trip_config.project
        credential = trip_config.remote_credential

        # Create RemoteProjectConfig if not exists
        if not RemoteProjectConfig.objects.filter(project=project).exists():
            RemoteProjectConfig.objects.create(
                project=project,
                ssh_host=credential.ssh_host,
                ssh_port=credential.ssh_port,
                ssh_username=credential.ssh_username,
                remote_credential=credential,
                remote_path=trip_config.remote_path,
                connection_mode="trip",
            )

        # Update project type
        project.project_type = "remote"
        project.save(update_fields=["project_type"])


def reverse_migration(apps, schema_editor):
    """Reverse: convert remote/trip back to trip type."""
    pass  # Not reversible cleanly


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0034_merge_trip_into_remote"),
    ]

    operations = [
        migrations.RunPython(convert_trip_to_remote, reverse_migration),
    ]
