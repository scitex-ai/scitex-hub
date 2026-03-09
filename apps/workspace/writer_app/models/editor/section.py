"""Manuscript section models."""

from django.db import models


class ManuscriptSection(models.Model):
    """Sections within a manuscript."""

    SECTION_TYPES = [
        ("abstract", "Abstract"),
        ("introduction", "Introduction"),
        ("methods", "Methods"),
        ("results", "Results"),
        ("discussion", "Discussion"),
        ("conclusion", "Conclusion"),
        ("references", "References"),
        ("appendix", "Appendix"),
        ("custom", "Custom Section"),
    ]

    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="sections"
    )
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField(default=0)

    improvement_suggestions = models.JSONField(default=list)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        unique_together = ["manuscript", "order"]

    def __str__(self):
        return f"{self.manuscript.title} - {self.title}"
