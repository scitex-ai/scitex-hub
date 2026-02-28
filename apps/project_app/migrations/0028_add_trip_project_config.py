# Generated manually for TRIP project support

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project_app", "0027_project_app_category_project_app_license_and_more"),
    ]

    operations = [
        # Update project_type choices to include "trip"
        migrations.AlterField(
            model_name="project",
            name="project_type",
            field=models.CharField(
                choices=[
                    ("local", "Local Repository"),
                    ("remote", "Remote Filesystem"),
                    ("trip", "Remote TRIP"),
                ],
                default="local",
                max_length=20,
            ),
        ),
        # Create TripProjectConfig model
        migrations.CreateModel(
            name="TripProjectConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "remote_path",
                    models.CharField(
                        help_text="Absolute path on remote system (e.g., /home/username/project)",
                        max_length=500,
                    ),
                ),
                (
                    "last_accessed",
                    models.DateTimeField(
                        blank=True,
                        help_text="Last time remote was accessed",
                        null=True,
                    ),
                ),
                (
                    "last_test_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Last connection test timestamp",
                        null=True,
                    ),
                ),
                (
                    "last_test_success",
                    models.BooleanField(
                        default=False,
                        help_text="Whether last connection test succeeded",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.OneToOneField(
                        help_text="Associated project",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trip_config",
                        to="project_app.project",
                    ),
                ),
                (
                    "remote_credential",
                    models.ForeignKey(
                        help_text="SSH credential for authentication",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trip_projects",
                        to="project_app.remotecredential",
                    ),
                ),
            ],
            options={
                "verbose_name": "TRIP Project Configuration",
                "verbose_name_plural": "TRIP Project Configurations",
            },
        ),
    ]
