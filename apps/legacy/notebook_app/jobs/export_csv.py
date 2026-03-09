#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export all experiments for a project to CSV.

Registered job handler: apps.notebook_app.jobs.export_csv.execute
Timeout: 60s | Rate limit: 30/hour
"""

from __future__ import annotations


def execute(job_id: int, **params) -> dict:
    """Export all experiments for a project to CSV via FileVault."""
    from apps.platform_app.models import PlatformJob
    from apps.platform_app.services.datastore import get_engine
    from apps.platform_app.services.filevault import FileVault

    job = PlatformJob.objects.get(pk=job_id)
    engine = get_engine("notebook", "Experiment")
    experiments = engine.filter(project=job.project)

    lines = ["title,date,status,notes"]
    for exp in experiments:
        d = exp.data
        title = str(d.get("title", "")).replace('"', '""')
        date = str(d.get("date", ""))
        status = str(d.get("status", ""))
        notes = str(d.get("notes", "")).replace('"', '""')
        lines.append(f'"{title}","{date}","{status}","{notes}"')

    csv_content = "\n".join(lines)
    vault = FileVault("notebook", job.project, job.owner)
    vault.save("exports/experiments.csv", csv_content)

    return {"file": "exports/experiments.csv", "count": len(experiments)}


# EOF
