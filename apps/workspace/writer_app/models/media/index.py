#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-project media index: discovered figure/table files and their metadata.

WHY THESE MODELS EXIST
----------------------
These replace ``writer_app/utils/project_db/`` — a hand-rolled, per-project
database that opened its own connection, declared its own schema, ran its own
ad-hoc migrations, and stored one file per project at
``{project_root}/scitex/metadata.db``. That is exactly the per-package database
layer the 2026-08-29 fleet ruling removed: every hand-rolled store is another
chance to re-derive the same data-loss and concurrency bugs, and this one had
already accumulated several (see BEHAVIOUR CHANGES below).

The rows are a REBUILDABLE INDEX, not a system of record. The truth is the
project's filesystem; ``writer_app.tasks.indexer`` walks it and upserts here.
Deleting every row costs one re-index, which is why moving the store needed no
data migration.

WHY THE DJANGO ORM AND NOT ``scitex_dev.store``
-----------------------------------------------
The fleet primitive is the right answer when a package needs a store of its
own. This app already has one: a Django ``DATABASES["default"]`` on the same
PostgreSQL cluster, with migrations, connection pooling and a transaction
story already wired up. Every consumer of this data is Django code (two Celery
tasks and three views) that is already inside an ORM context, and every row is
scoped to a ``Project`` row that only the ORM can resolve. Introducing a second
datastore alongside Django's own — with its own DSN, its own schema and its own
migration path — would add a store rather than remove one, which is the
opposite of what the ruling asked for. So: no hand-rolled layer, no second
store, no embedded database. Django's ORM is the store.

BEHAVIOUR CHANGES, stated rather than buried
--------------------------------------------
1. ``ProjectTable.file_size`` is NEW. The old ``tables`` table had no such
   column, but the old duplicate-detection query selected it — so table
   dedup raised ``no such column: file_size`` on every call and was swallowed
   by a bare ``except Exception``. Table dedup has never worked; it does now.
2. Uniqueness is now ``(project, file_path)``. The old file-per-project layout
   made ``file_path`` alone unique; carrying that verbatim into a shared table
   would have let one project's re-index clobber another's row.
3. Search used the old engine's bundled full-text extension (a ``MATCH``
   query over a virtual table kept in sync by three triggers) and is now
   case-insensitive substring matching over the same three fields. Relevance
   ranking is gone; substring matching finds strictly more rows for the
   partial-filename queries this endpoint actually receives.
"""

from django.db import models


class ProjectFigure(models.Model):
    """A figure file discovered in a project, with its indexing metadata."""

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="writer_figures",
    )

    # Identity
    file_path = models.TextField(help_text="Path relative to the project root")
    file_name = models.TextField()
    file_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=32, db_index=True)

    # Metadata
    last_modified = models.FloatField(default=0.0)
    thumbnail_path = models.TextField(blank=True, default="")

    # Auto-extracted
    tags = models.JSONField(default=list, blank=True)
    is_referenced = models.BooleanField(default=False, db_index=True)
    reference_count = models.IntegerField(default=0)

    # Discovery info
    source = models.CharField(max_length=64, blank=True, default="", db_index=True)
    location = models.TextField(blank=True, default="")

    # Index tracking
    indexed_at = models.FloatField(default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "file_path"],
                name="uniq_writer_projectfigure_project_filepath",
            )
        ]
        indexes = [
            models.Index(fields=["project", "last_modified"]),
            models.Index(fields=["project", "file_hash"]),
        ]
        ordering = ["-last_modified"]

    def __str__(self):
        return f"{self.file_name} ({self.project_id})"


class ProjectTable(models.Model):
    """A table file (CSV/Excel/TSV) discovered in a project."""

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="writer_tables",
    )

    file_path = models.TextField(help_text="Path relative to the project root")
    file_name = models.TextField()
    file_hash = models.CharField(max_length=64, db_index=True)
    # See BEHAVIOUR CHANGES (1) in the module docstring: this column is new,
    # and its absence is why table duplicate-detection silently never ran.
    file_size = models.BigIntegerField(default=0)
    caption = models.TextField(blank=True, default="")

    last_modified = models.FloatField(default=0.0)
    thumbnail_path = models.TextField(blank=True, default="")

    tags = models.JSONField(default=list, blank=True)
    is_referenced = models.BooleanField(default=False, db_index=True)
    reference_count = models.IntegerField(default=0)

    source = models.CharField(max_length=64, blank=True, default="", db_index=True)
    location = models.TextField(blank=True, default="")

    indexed_at = models.FloatField(default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "file_path"],
                name="uniq_writer_projecttable_project_filepath",
            )
        ]
        indexes = [
            models.Index(fields=["project", "last_modified"]),
            models.Index(fields=["project", "file_hash"]),
        ]
        ordering = ["-last_modified"]

    def __str__(self):
        return f"{self.file_name} ({self.project_id})"


class ProjectFigureLatexReference(models.Model):
    """One \\ref/\\includegraphics site in a .tex file pointing at a figure."""

    figure = models.ForeignKey(
        ProjectFigure,
        on_delete=models.CASCADE,
        related_name="latex_references",
    )
    tex_file = models.TextField()
    line_number = models.IntegerField(null=True, blank=True)
    context = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["figure"])]

    def __str__(self):
        return f"{self.tex_file}:{self.line_number}"


# EOF
