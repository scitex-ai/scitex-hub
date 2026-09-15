"""Run schedulable, secret-safe production credential probes."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.infra.public_app.services.credential_health import (
    ALLOWED_STATUSES,
    credential_inventory,
    run_credential_preflight,
)


class Command(BaseCommand):
    help = "Probe production credentials without printing credential material"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--inventory", action="store_true")
        parser.add_argument(
            "--force-status",
            action="append",
            default=[],
            metavar="ID=STATUS",
            help="Test/monitoring drill control; bypasses reads and network for ID",
        )

    def handle(self, *args, **options):
        if options["inventory"]:
            self.stdout.write(json.dumps({"credentials": credential_inventory()}, sort_keys=True))
            return
        forced = {}
        valid_ids = {item["id"] for item in credential_inventory()}
        for item in options["force_status"]:
            try:
                credential_id, status = item.split("=", 1)
            except ValueError as exc:
                raise CommandError("--force-status requires ID=STATUS") from exc
            if credential_id not in valid_ids or status not in ALLOWED_STATUSES:
                raise CommandError("Unsupported credential id or status")
            forced[credential_id] = status
        report = run_credential_preflight(forced_statuses=forced)
        self.stdout.write(json.dumps(report, sort_keys=True))
        if report["overall"] != "healthy":
            raise CommandError("Credential preflight failed")
