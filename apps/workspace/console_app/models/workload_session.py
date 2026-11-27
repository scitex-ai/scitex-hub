"""One row per workload the Hub launches on a scheduler.

This is the join table that usage collectors resolve ``sacct`` rows
against: a SLURM job's ``--comment`` carries ``session:<session_id>`` and
the row records who launched it, for which project, and when it stopped.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkloadSession(models.Model):
    WORKLOAD_TERMINAL = "terminal"
    WORKLOAD_JOB = "job"
    WORKLOAD_CHOICES = [
        (WORKLOAD_TERMINAL, "Terminal"),
        (WORKLOAD_JOB, "Batch job"),
    ]

    SCHEDULER_SLURM = "slurm"
    SCHEDULER_CHOICES = [(SCHEDULER_SLURM, "SLURM")]

    # Equals the ``session:`` value in the job's --comment.
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # SET_NULL: usage records outlive the user and the project. ``tags``
    # keeps the ids that were attributed at launch.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="workload_sessions",
    )
    # Null when the launch genuinely had no project (tagged ``project:none``).
    project = models.ForeignKey(
        "project_app.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workload_sessions",
    )
    workload = models.CharField(max_length=20, choices=WORKLOAD_CHOICES)
    scheduler = models.CharField(
        max_length=20, choices=SCHEDULER_CHOICES, default=SCHEDULER_SLURM
    )
    # Blank until the scheduler returns an id, and for interactive
    # ``srun --pty`` shells, whose job id the Hub never sees (join on
    # session_id instead).
    scheduler_job_id = models.CharField(max_length=64, blank=True, db_index=True)
    # Host the Hub submitted from.
    host = models.CharField(max_length=255)
    tags = models.JSONField(default=dict)
    started_at = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["scheduler", "scheduler_job_id"]),
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["project", "started_at"]),
        ]

    def __str__(self):
        job = self.scheduler_job_id or "-"
        return f"{self.workload} {self.scheduler}:{job} session={self.session_id}"
