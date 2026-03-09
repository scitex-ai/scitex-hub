from django.db import models
import uuid


class Author(models.Model):
    """Author information for research papers"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    orcid = models.CharField(
        max_length=19, blank=True, db_index=True
    )  # ORCID format: 0000-0000-0000-0000
    email = models.EmailField(blank=True)
    affiliation = models.CharField(max_length=500, blank=True)
    h_index = models.IntegerField(null=True, blank=True)
    total_citations = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["orcid"]),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)


class Journal(models.Model):
    """Journal metadata"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500, unique=True)
    abbreviation = models.CharField(max_length=100, blank=True)
    issn = models.CharField(
        max_length=9, blank=True, db_index=True
    )  # Format: 0000-0000
    eissn = models.CharField(max_length=9, blank=True)  # Electronic ISSN
    publisher = models.CharField(max_length=200, blank=True)
    impact_factor = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    website = models.URLField(blank=True)
    open_access = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["issn"]),
        ]

    def __str__(self):
        return self.name


class Topic(models.Model):
    """Research topics/keywords"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    description = models.TextField(blank=True)
    paper_count = models.IntegerField(default=0)  # Denormalized for performance
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class SearchIndex(models.Model):
    """Main search index for documents and research papers"""

    SOURCE_CHOICES = [
        ("pubmed", "PubMed"),
        ("arxiv", "arXiv"),
        ("doi", "DOI"),
        ("google_scholar", "Google Scholar"),
        ("internal", "Internal"),
        ("manual", "Manual Entry"),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ("article", "Journal Article"),
        ("preprint", "Preprint"),
        ("book", "Book"),
        ("chapter", "Book Chapter"),
        ("conference", "Conference Paper"),
        ("thesis", "Thesis/Dissertation"),
        ("report", "Technical Report"),
        ("dataset", "Dataset"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("archived", "Archived"),
        ("retracted", "Retracted"),
        ("pending", "Pending Review"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic metadata
    title = models.TextField(db_index=True)
    abstract = models.TextField(blank=True)
    document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPE_CHOICES, default="article"
    )
    publication_date = models.DateField(null=True, blank=True, db_index=True)

    # Authors and affiliations
    authors = models.ManyToManyField(Author, through="AuthorPaper")
    journal = models.ForeignKey(
        Journal, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Identifiers
    doi = models.CharField(
        max_length=100, blank=True, unique=True, null=True, db_index=True
    )
    pmid = models.CharField(
        max_length=20, blank=True, unique=True, null=True, db_index=True
    )  # PubMed ID
    arxiv_id = models.CharField(
        max_length=20, blank=True, unique=True, null=True, db_index=True
    )
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="manual"
    )  # Legacy single source
    source_engines = models.JSONField(
        default=list,
        blank=True,
        help_text="List of search engines that found this paper (e.g., ['PubMed', 'CrossRef'])",
    )
    external_url = models.URLField(blank=True)

    # Content
    full_text = models.TextField(blank=True)
    pdf_url = models.URLField(blank=True)
    pdf_file = models.FileField(upload_to="scholar/pdfs/", blank=True, null=True)
    bibtex_file = models.FileField(upload_to="scholar/bibtex/", blank=True, null=True)
    bibtex_content = models.TextField(blank=True, help_text="BibTeX citation content")

    # Search optimization
    # search_vector = SearchVectorField(null=True)  # PostgreSQL full-text search - commented for compatibility
    keywords = models.TextField(
        blank=True
    )  # Store as comma-separated values for SQLite compatibility
    topics = models.ManyToManyField(Topic, blank=True)

    # Metrics
    citation_count = models.IntegerField(default=0)
    citation_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of citation data (semantic_scholar, crossref, etc.)",
    )
    citation_last_updated = models.DateTimeField(
        null=True, blank=True, help_text="When citation count was last updated"
    )
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    relevance_score = models.FloatField(default=0.0)  # Custom relevance scoring

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    is_open_access = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    indexed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-publication_date", "-relevance_score"]
        indexes = [
            models.Index(fields=["publication_date", "relevance_score"]),
            models.Index(fields=["doi"]),
            models.Index(fields=["pmid"]),
            models.Index(fields=["arxiv_id"]),
            # GinIndex(fields=['search_vector']),  # PostgreSQL specific - commented for compatibility
        ]

    def __str__(self):
        return self.title[:100]


class AuthorPaper(models.Model):
    """Through model for Author-Paper relationship with ordering"""

    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    paper = models.ForeignKey(SearchIndex, on_delete=models.CASCADE)
    author_order = models.IntegerField(default=1)
    is_corresponding = models.BooleanField(default=False)

    class Meta:
        ordering = ["author_order"]
        unique_together = ["author", "paper"]


class Citation(models.Model):
    """Paper citations and references"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    citing_paper = models.ForeignKey(
        SearchIndex, on_delete=models.CASCADE, related_name="citations_made"
    )
    cited_paper = models.ForeignKey(
        SearchIndex, on_delete=models.CASCADE, related_name="citations_received"
    )
    citation_context = models.TextField(blank=True)  # Text around the citation
    section = models.CharField(
        max_length=50, blank=True
    )  # Section where citation appears
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["citing_paper", "cited_paper"]
        indexes = [
            models.Index(fields=["citing_paper", "cited_paper"]),
        ]

    def __str__(self):
        return f"{self.citing_paper.title[:50]} cites {self.cited_paper.title[:50]}"
