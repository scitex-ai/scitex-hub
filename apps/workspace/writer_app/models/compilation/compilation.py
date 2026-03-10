"""Compilation and AI assistance models for writer_app."""

from django.db import models
from django.contrib.auth.models import User
import uuid


class CompilationJob(models.Model):
    """Track LaTeX compilation jobs."""

    JOB_STATUS = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    COMPILATION_TYPES = [
        ("full", "Full Compilation"),
        ("draft", "Draft Mode"),
        ("quick", "Quick Preview"),
    ]

    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="compilation_jobs"
    )
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    initiated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="compilation_jobs"
    )

    # Compilation details
    compilation_type = models.CharField(
        max_length=20, choices=COMPILATION_TYPES, default="full"
    )

    # Status and results
    status = models.CharField(max_length=20, choices=JOB_STATUS, default="queued")
    output_pdf = models.FileField(upload_to="compilations/", blank=True, null=True)
    output_path = models.CharField(
        max_length=500, blank=True
    )  # Temporary path for downloads
    log_file = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    error_log = models.TextField(blank=True)  # Detailed error logs

    # Metrics
    compilation_time = models.FloatField(null=True, blank=True)  # in seconds
    page_count = models.IntegerField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Compilation {self.job_id} - {self.status}"


class AIAssistanceLog(models.Model):
    """Track AI assistance usage."""

    ASSISTANCE_TYPES = [
        ("content", "Content Generation"),
        ("revision", "Text Revision"),
        ("citation", "Citation Suggestion"),
        ("grammar", "Grammar Check"),
        ("style", "Style Improvement"),
        ("generate_section", "Section Generation"),
    ]

    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="ai_logs"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Assistance details
    assistance_type = models.CharField(max_length=20, choices=ASSISTANCE_TYPES)
    section_type = models.CharField(
        max_length=50, blank=True
    )  # Type of section being generated

    # Content
    prompt = models.TextField(blank=True)  # User's prompt/request
    original_text = models.TextField(blank=True)
    suggested_text = models.TextField(blank=True)
    generated_text = models.TextField(blank=True)  # AI-generated content
    accepted = models.BooleanField(default=False)

    # Section-specific generation
    target_section = models.CharField(
        max_length=50, blank=True
    )  # Which section is being worked on
    word_count_target = models.IntegerField(
        null=True, blank=True
    )  # Target word count for generation

    # Metrics
    tokens_used = models.IntegerField(default=0)
    response_time = models.FloatField(null=True, blank=True)  # in seconds

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_assistance_type_display()} - {self.manuscript.title[:50]}"
