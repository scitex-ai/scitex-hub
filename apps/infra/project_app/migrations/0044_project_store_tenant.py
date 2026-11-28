"""Provisioned Clew store tenants (per owner) and scopes (per project)."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("project_app", "0043_app_store_copy"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectStoreTenant",
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
                    "tenant_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("dsn", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_store_tenant",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Project store tenant"},
        ),
        migrations.CreateModel(
            name="ProjectStoreScope",
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
                ("scope", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="store_scope",
                        to="project_app.project",
                    ),
                ),
            ],
            options={"verbose_name": "Project store scope"},
        ),
    ]
