"""One row per workload the Hub launches: terminal, batch job, or project service.

This is the join table that usage collectors resolve ``sacct`` rows
against: a SLURM job's ``--comment`` carries ``session:<session_id>`` and
the row records who launched it, for which project, and when it stopped.

It is also the compute source of spend controls (``spend_app.services.usage``
bills allocation x wall time from it), so it records the allocated resources
and why the workload stopped. One launch is one row; nothing else in the Hub
keeps a second launch record.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkloadSession(models.Model):
    WORKLOAD_TERMINAL = "terminal"
    WORKLOAD_JOB = "job"
    WORKLOAD_SERVICE = "service"
    WORKLOAD_CHOICES = [
        (WORKLOAD_TERMINAL, "Terminal"),
        (WORKLOAD_JOB, "Batch job"),
        (WORKLOAD_SERVICE, "Project service (notebook, TensorBoard, ...)"),
    ]

    SCHEDULER_SLURM = "slurm"
    # A process the Hub starts on its own host (project services).
    SCHEDULER_LOCAL = "local"
    SCHEDULER_CHOICES = [
        (SCHEDULER_SLURM, "SLURM"),
        (SCHEDULER_LOCAL, "Hub host process"),
    ]

    class StopReason(models.TextChoices):
        NONE = "", "Running (or stop not attributed)"
        COMPLETED = "completed", "Finished on its own"
        USER = "user", "Stopped by the user"
        IDLE = "idle", "Idle auto-stop"
        SPEND_CAP = "spend_cap", "Monthly spend cap reached"
        RESTRICTED = "restricted", "Account restricted"
        EXPIRED = "expired", "Time limit reached"
        LOST = "lost", "Ended without a stop record"

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
    # session_id instead). For a project service, its ``service_id``.
    scheduler_job_id = models.CharField(max_length=64, blank=True, db_index=True)
    # Host the Hub submitted from.
    host = models.CharField(max_length=255)
    tags = models.JSONField(default=dict)
    started_at = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stop_reason = models.CharField(
        max_length=16, choices=StopReason.choices, blank=True, default=""
    )

    # Allocated (reserved) resources: compute is billed by allocation.
    cpus = models.PositiveSmallIntegerField(default=1)
    memory_gb = models.PositiveSmallIntegerField(default=4)
    gpus = models.PositiveSmallIntegerField(default=0)
    # Upper bound on billed wall time when no stop is ever recorded (a SLURM
    # job's time limit). ``None`` = open until stopped.
    max_seconds = models.PositiveIntegerField(null=True, blank=True)
    # Human-readable name: job name, service type, ``interactive``.
    label = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["scheduler", "scheduler_job_id"]),
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["project", "started_at"]),
            models.Index(fields=["user", "stopped_at"]),
        ]

    def __str__(self):
        job = self.scheduler_job_id or "-"
        return f"{self.workload} {self.scheduler}:{job} session={self.session_id}"
