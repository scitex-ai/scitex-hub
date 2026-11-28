"""Provision the private Clew store of existing projects ahead of first use.

Projects get their store on the first Clew request anyway; this command lets
an operator do it in bulk (after enabling SCITEX_HUB_STORE_PROVISIONER_DSN on
a deployment) and see which projects cannot be provisioned. Idempotent.
Projects an operator configured by hand in SCITEX_HUB_STORE_TENANT_SECRETS
are skipped. Prints project ids and outcomes only, never a credential.

    python manage.py provision_project_stores --project 229
    python manage.py provision_project_stores --all
"""

from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_store_provisioning import (
    ProvisioningUnavailable,
    provision_project_store,
    provisioning_configured,
)


def _hand_configured() -> dict:
    configuration = getattr(settings, "SCITEX_STORE_TENANT_SECRETS", {}) or {}
    if isinstance(configuration, str):
        configuration = json.loads(configuration) if configuration.strip() else {}
    return configuration if isinstance(configuration, dict) else {}


class Command(BaseCommand):
    help = "Provision the private Clew store (tenant + project scope) of projects."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--project", type=int, action="append", dest="projects")
        target.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if not provisioning_configured():
            raise CommandError("SCITEX_HUB_STORE_PROVISIONER_DSN is not set")
        projects = Project.objects.select_related("owner").order_by("pk")
        if not options["all"]:
            projects = projects.filter(pk__in=options["projects"])
        configured = _hand_configured()
        failures = 0
        for project in projects:
            entry = configured.get(str(project.owner_id)) or {}
            if str(project.pk) in (entry.get("projects") or {}):
                self.stdout.write(f"{project.pk}\tskipped (hand-configured)")
                continue
            try:
                provision_project_store(project)
            except ProvisioningUnavailable as exc:
                failures += 1
                self.stdout.write(f"{project.pk}\tFAILED ({exc})")
                continue
            self.stdout.write(f"{project.pk}\tok")
        if failures:
            raise CommandError(f"{failures} project(s) could not be provisioned")
