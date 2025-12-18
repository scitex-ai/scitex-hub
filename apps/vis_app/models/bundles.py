"""
Bundle Models for Plot and Figure Storage

PltzBundle - Reproducible plot specification (.pltz)
FigzBundle - Multi-panel publication figure (.figz)
FigzPanel - Through model linking figures to plot panels
"""

import uuid

from django.contrib.auth.models import User
from django.db import models

from .figures import JournalPreset


class PltzBundle(models.Model):
    """
    Plot bundle (.pltz) - Reproducible plot specification.

    Directory structure (*.pltz.d/):
        spec.json     - WHAT to plot (canonical)
        style.json    - HOW it looks (canonical)
        data.csv      - Raw data (immutable)
        exports/      - Preview images (plot.png, plot_hitmap.png)
        cache/        - Derived geometry (geometry_px.json, render_manifest.json)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pltz_bundles"
    )

    # Bundle identification
    name = models.CharField(max_length=200, help_text="Display name for the plot")
    slug = models.SlugField(max_length=200, help_text="URL-safe identifier")

    # Bundle storage
    bundle_path = models.CharField(
        max_length=500, help_text="Path to .pltz.d directory or .pltz ZIP file"
    )
    is_zip = models.BooleanField(
        default=False, help_text="True if stored as ZIP, False if directory"
    )

    # Canonical spec and style (cached for quick access)
    spec = models.JSONField(
        default=dict, help_text="PltzSpec: plot_id, data, axes, traces"
    )
    style = models.JSONField(
        default=dict, help_text="PltzStyle: theme, size, font, traces, legend"
    )

    # Data tracking
    data_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of data.csv for integrity verification",
    )
    data_format = models.CharField(
        max_length=20, default="wide", help_text="Data format: 'wide' or 'long'"
    )

    # Categorization
    CATEGORY_CHOICES = [
        ("line", "Line Plots"),
        ("scatter", "Scatter Plots"),
        ("bar", "Bar Charts"),
        ("distribution", "Distributions"),
        ("statistical", "Statistical"),
        ("heatmap", "Heatmaps"),
        ("contour", "Contours"),
        ("other", "Other"),
    ]
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="other"
    )

    # Metadata
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, help_text="List of tags for filtering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["owner", "slug"]
        indexes = [
            models.Index(fields=["owner", "category"]),
            models.Index(fields=["data_hash"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"

    def get_export_path(self, filename: str) -> str:
        """Get path to exported file within bundle."""
        from pathlib import Path

        return str(Path(self.bundle_path) / "exports" / filename)

    def get_cache_path(self, filename: str) -> str:
        """Get path to cached file within bundle."""
        from pathlib import Path

        return str(Path(self.bundle_path) / "cache" / filename)


class FigzBundle(models.Model):
    """
    Figure bundle (.figz) - Multi-panel publication figure.

    Directory structure (*.figz.d/):
        spec.json     - Figure specification (layout, panels)
        style.json    - Figure style (theme, fonts)
        exports/      - Composed figure images
        cache/        - Combined geometry from all panels
        A.pltz.d/     - Nested plot bundle for panel A
        B.pltz.d/     - Nested plot bundle for panel B
        ...
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="figz_bundles"
    )

    # Bundle identification
    name = models.CharField(max_length=200, help_text="Figure title")
    slug = models.SlugField(max_length=200, help_text="URL-safe identifier")

    # Bundle storage
    bundle_path = models.CharField(
        max_length=500, help_text="Path to .figz.d directory or .figz ZIP file"
    )
    is_zip = models.BooleanField(
        default=False, help_text="True if stored as ZIP, False if directory"
    )

    # Canonical spec and style
    spec = models.JSONField(
        default=dict, help_text="FigureSpec: figure_id, layout, panels"
    )
    style = models.JSONField(
        default=dict, help_text="FigureStyle: theme, fonts, spacing"
    )

    # Panel relationships
    panels = models.ManyToManyField(
        PltzBundle,
        through="FigzPanel",
        related_name="parent_figures",
        help_text="Plot bundles used as panels in this figure",
    )

    # Layout configuration
    LAYOUT_CHOICES = [
        ("1x1", "Single Panel"),
        ("2x1", "Two Horizontal"),
        ("1x2", "Two Vertical"),
        ("2x2", "Four Panel Grid"),
        ("1x3", "Three Horizontal"),
        ("3x1", "Three Vertical"),
        ("2x3", "Six Panel Grid"),
        ("custom", "Custom Layout"),
    ]
    layout = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default="1x1")

    # Export settings
    width_mm = models.FloatField(default=170.0, help_text="Figure width in mm")
    height_mm = models.FloatField(
        null=True, blank=True, help_text="Figure height in mm (auto if null)"
    )
    dpi = models.IntegerField(default=300)

    # Journal preset (optional)
    journal_preset = models.ForeignKey(
        JournalPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="figz_bundles",
    )

    # Metadata
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["owner", "slug"]
        verbose_name = "Figure Bundle"
        verbose_name_plural = "Figure Bundles"

    def __str__(self):
        return f"{self.name} ({self.layout})"

    def get_panel_count(self):
        """Get number of panels in this figure."""
        return self.figz_panels.count()


class FigzPanel(models.Model):
    """
    Through model linking FigzBundle to PltzBundle panels.

    Tracks panel position, label, and layout within the figure.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    figure = models.ForeignKey(
        FigzBundle, on_delete=models.CASCADE, related_name="figz_panels"
    )
    plot = models.ForeignKey(
        PltzBundle, on_delete=models.CASCADE, related_name="panel_usages"
    )

    # Panel identification
    LABEL_CHOICES = [(chr(65 + i), f"Panel {chr(65 + i)}") for i in range(8)]  # A-H
    label = models.CharField(max_length=1, choices=LABEL_CHOICES, default="A")
    order = models.IntegerField(default=0, help_text="Panel order in layout")

    # Position within figure canvas (normalized 0-1)
    x = models.FloatField(default=0.0, help_text="X position (0-1)")
    y = models.FloatField(default=0.0, help_text="Y position (0-1)")
    width = models.FloatField(default=1.0, help_text="Width (0-1)")
    height = models.FloatField(default=1.0, help_text="Height (0-1)")

    # Per-panel style overrides (optional)
    style_overrides = models.JSONField(
        default=dict, help_text="Style overrides for this panel only"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "label"]
        unique_together = ["figure", "label"]

    def __str__(self):
        return f"Panel {self.label} of {self.figure.name}"
