"""Manuscript references and figures models."""

from django.db import models


class Figure(models.Model):
    """Figures and images in manuscripts."""

    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="figures"
    )

    # Figure details
    label = models.CharField(max_length=100)  # LaTeX label
    caption = models.TextField()
    file = models.ImageField(upload_to="manuscripts/figures/")

    # Positioning
    position = models.CharField(max_length=10, default="htbp")  # LaTeX positioning
    width = models.FloatField(default=1.0)  # Fraction of textwidth

    # Order and references
    order = models.IntegerField(default=0)
    referenced_in_sections = models.ManyToManyField("ManuscriptSection", blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Figure {self.order}: {self.label}"


class Table(models.Model):
    """Tables in manuscripts."""

    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="tables"
    )

    # Table details
    label = models.CharField(max_length=100)
    caption = models.TextField()
    content = models.TextField()  # LaTeX table content

    # Data source
    data_file = models.FileField(upload_to="manuscripts/tables/", blank=True, null=True)

    # Positioning
    position = models.CharField(max_length=10, default="htbp")

    # Order and references
    order = models.IntegerField(default=0)
    referenced_in_sections = models.ManyToManyField("ManuscriptSection", blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Table {self.order}: {self.label}"


class Citation(models.Model):
    """Bibliography entries and citations."""

    ENTRY_TYPES = [
        ("article", "Journal Article"),
        ("book", "Book"),
        ("inproceedings", "Conference Paper"),
        ("techreport", "Technical Report"),
        ("phdthesis", "PhD Thesis"),
        ("misc", "Miscellaneous"),
    ]

    # Citation key and manuscript
    citation_key = models.CharField(max_length=100)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="citations"
    )

    # Bibliographic information
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    authors = models.TextField()
    title = models.CharField(max_length=500)
    year = models.IntegerField()

    # Additional fields
    journal = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=20, blank=True)
    number = models.CharField(max_length=20, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)

    # BibTeX entry
    bibtex_entry = models.TextField()

    # Usage tracking
    cited_in_sections = models.ManyToManyField("ManuscriptSection", blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["manuscript", "citation_key"]
        ordering = ["authors", "year"]

    def __str__(self):
        return f"[{self.citation_key}] {self.authors[:50]}... ({self.year})"
