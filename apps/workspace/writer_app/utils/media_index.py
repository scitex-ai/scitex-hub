#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Accessor for a project's figure/table media index.

This replaces ``writer_app/utils/project_db/`` (7 files, 851 lines), which
opened its own connections, declared its own schema and ran its own ad-hoc
migrations against one embedded database file per project. The rows now live
in ordinary Django models — see ``writer_app/models/media/index.py`` for why
the ORM and not ``scitex_dev.store``.

What is left here is deliberately NOT a database layer: it holds no
connection, defines no schema, and issues no SQL. It is a small service object
that resolves a project's filesystem root (for the thumbnail directory) and
forwards queries to the ORM, so the indexer tasks and media views keep reading
the same shapes they always did.
"""

import logging
import time
from pathlib import Path

from django.db.models import Count, Q, Sum

from apps.workspace.writer_app.models.media.index import (
    ProjectFigure,
    ProjectFigureLatexReference,
    ProjectTable,
)

logger = logging.getLogger(__name__)

# Fields returned to callers, in the order the old row dicts carried them.
_FIGURE_FIELDS = (
    "id",
    "file_path",
    "file_name",
    "file_hash",
    "file_size",
    "file_type",
    "last_modified",
    "thumbnail_path",
    "tags",
    "is_referenced",
    "reference_count",
    "source",
    "location",
    "indexed_at",
)

_TABLE_FIELDS = (
    "id",
    "file_path",
    "file_name",
    "file_hash",
    "file_size",
    "caption",
    "last_modified",
    "thumbnail_path",
    "tags",
    "is_referenced",
    "reference_count",
    "source",
    "location",
    "indexed_at",
)


def _resolve_project_path(project) -> Path:
    """Return the filesystem root of ``project``.

    Lifted verbatim from the old ``get_project_db`` so thumbnail placement and
    the indexer's relative paths are unchanged.
    """
    if getattr(project, "git_clone_path", None):
        project_path = Path(project.git_clone_path)
        logger.debug(
            f"[MediaIndex] Using git_clone_path for project {project.id}: {project_path}"
        )
        return project_path

    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        if not getattr(project, "owner", None):
            raise ValueError(f"Project {project.id} has no owner")

        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path:
            raise ValueError(
                f"Project path not found for project {project.id} "
                f"(slug: {project.slug})"
            )

        logger.info(
            f"[MediaIndex] Using filesystem manager path for project "
            f"{project.id}: {project_path}"
        )
        return project_path
    except Exception as e:
        logger.error(f"[MediaIndex] Could not determine project path: {e}", exc_info=True)
        raise ValueError(
            f"Cannot determine project path for project {project.id}: {e}"
        )


class ProjectMediaIndex:
    """Query/update a single project's indexed figures and tables."""

    def __init__(self, project):
        self.project = project
        self.project_path = _resolve_project_path(project)
        self.scitex_dir = self.project_path / "scitex"
        self.thumbnails_dir = self.scitex_dir / "thumbnails"

        # The thumbnail directory used to be created as a side effect of
        # opening the per-project database. Nothing else creates it, and
        # tasks/indexer/thumbnails.py writes into it directly, so keep doing
        # it here. parents=True (the old code omitted it) so a project root
        # that exists but has no scitex/ dir does not raise.
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    # -- figures ---------------------------------------------------------

    def upsert_figure(self, metadata: dict):
        """Insert or update one figure row, keyed on (project, file_path)."""
        ProjectFigure.objects.update_or_create(
            project=self.project,
            file_path=metadata["file_path"],
            defaults={
                "file_name": metadata["file_name"],
                "file_hash": metadata["file_hash"],
                "file_size": metadata["file_size"],
                "file_type": metadata["file_type"],
                "last_modified": metadata["last_modified"],
                "thumbnail_path": metadata.get("thumbnail_path") or "",
                "tags": metadata.get("tags", []),
                "is_referenced": bool(metadata.get("is_referenced", False)),
                "reference_count": metadata.get("reference_count", 0),
                "source": metadata.get("source", ""),
                "location": metadata.get("location", ""),
                "indexed_at": time.time(),
            },
        )
        logger.debug(f"[MediaIndex] Upserted figure: {metadata['file_name']}")

    def get_all_figures(self, filters=None):
        qs = ProjectFigure.objects.filter(project=self.project)
        if filters:
            if filters.get("source"):
                qs = qs.filter(source=filters["source"])
            if filters.get("is_referenced") is not None:
                qs = qs.filter(is_referenced=bool(filters["is_referenced"]))
            if filters.get("file_type"):
                qs = qs.filter(file_type=filters["file_type"])
        figures = list(qs.order_by("-last_modified").values(*_FIGURE_FIELDS))
        logger.debug(f"[MediaIndex] Retrieved {len(figures)} figures")
        return figures

    def search_figures(self, query: str):
        """Case-insensitive substring search over file_name / location / tags.

        The previous implementation used the old engine's bundled full-text
        extension, which is not available now. Substring matching returns a
        superset of what those partial-filename queries matched before.
        """
        qs = (
            ProjectFigure.objects.filter(project=self.project)
            .filter(
                Q(file_name__icontains=query)
                | Q(location__icontains=query)
                | Q(tags__icontains=query)
            )
            .order_by("-last_modified")
        )
        figures = list(qs.values(*_FIGURE_FIELDS))
        logger.debug(f"[MediaIndex] Search '{query}' found {len(figures)} figures")
        return figures

    def set_figure_thumbnail(self, file_path: str, thumbnail_path: str):
        """Record a generated thumbnail against an indexed figure."""
        ProjectFigure.objects.filter(
            project=self.project, file_path=file_path
        ).update(thumbnail_path=thumbnail_path)

    def delete_figure(self, file_path: str):
        ProjectFigure.objects.filter(
            project=self.project, file_path=file_path
        ).delete()
        logger.debug(f"[MediaIndex] Deleted figure: {file_path}")

    def get_stats(self):
        agg = ProjectFigure.objects.filter(project=self.project).aggregate(
            total=Count("id"),
            referenced=Count("id", filter=Q(is_referenced=True)),
            sources=Count("source", distinct=True),
            total_size=Sum("file_size"),
        )
        return {
            "total": agg["total"] or 0,
            "referenced": agg["referenced"] or 0,
            "sources": agg["sources"] or 0,
            "total_size": agg["total_size"] or 0,
        }

    # -- tables ----------------------------------------------------------

    def upsert_table(self, metadata: dict):
        ProjectTable.objects.update_or_create(
            project=self.project,
            file_path=metadata["file_path"],
            defaults={
                "file_name": metadata["file_name"],
                "file_hash": metadata["file_hash"],
                "file_size": metadata.get("file_size", 0),
                "caption": metadata.get("caption") or "",
                "last_modified": metadata["last_modified"],
                "thumbnail_path": metadata.get("thumbnail_path") or "",
                "tags": metadata.get("tags", []),
                "is_referenced": bool(metadata.get("is_referenced", False)),
                "reference_count": metadata.get("reference_count", 0),
                "source": metadata.get("source", ""),
                "location": metadata.get("location", ""),
                "indexed_at": time.time(),
            },
        )

    def get_all_tables(self, filters=None):
        qs = ProjectTable.objects.filter(project=self.project)
        if filters:
            if filters.get("source"):
                qs = qs.filter(source=filters["source"])
            if filters.get("is_referenced") is not None:
                qs = qs.filter(is_referenced=bool(filters["is_referenced"]))
        tables = list(qs.order_by("-last_modified").values(*_TABLE_FIELDS))
        logger.debug(f"[MediaIndex] Retrieved {len(tables)} tables")
        return tables

    def set_table_thumbnail(self, file_path: str, thumbnail_path: str):
        """Record a generated thumbnail against an indexed table."""
        ProjectTable.objects.filter(
            project=self.project, file_path=file_path
        ).update(thumbnail_path=thumbnail_path)

    def delete_table(self, file_path: str):
        ProjectTable.objects.filter(project=self.project, file_path=file_path).delete()
        logger.debug(f"[MediaIndex] Deleted table: {file_path}")

    # -- LaTeX references ------------------------------------------------

    def update_references(
        self, figure_id: int, is_referenced: bool, reference_count: int
    ):
        ProjectFigure.objects.filter(project=self.project, id=figure_id).update(
            is_referenced=bool(is_referenced), reference_count=reference_count
        )

    def add_latex_reference(
        self,
        figure_id: int,
        tex_file: str,
        line_number: int = None,
        context: str = None,
    ):
        ProjectFigureLatexReference.objects.create(
            figure_id=figure_id,
            tex_file=tex_file,
            line_number=line_number,
            context=context,
        )

    def clear_latex_references(self, figure_id: int):
        ProjectFigureLatexReference.objects.filter(figure_id=figure_id).delete()

    # -- change / duplicate detection ------------------------------------

    def check_if_indexed(
        self, file_path: str, file_hash: str, table_type: str = "figure"
    ) -> bool:
        """True when this path is already indexed with the same content hash."""
        model = ProjectTable if table_type == "table" else ProjectFigure
        return model.objects.filter(
            project=self.project, file_path=file_path, file_hash=file_hash
        ).exists()

    def check_hash_exists(self, file_hash: str, table_type: str = "figure"):
        """Return an already-indexed file with this content hash, or None.

        For tables this used to raise ``no such column: file_size`` on every
        call (the old table schema had no such column) and the exception was
        swallowed by the caller, so table dedup never ran. It runs now.
        """
        model = ProjectTable if table_type == "table" else ProjectFigure
        row = (
            model.objects.filter(project=self.project, file_hash=file_hash)
            .values("file_path", "file_name", "file_size")
            .first()
        )
        return dict(row) if row else None


def get_media_index(project) -> ProjectMediaIndex:
    """Return the media index accessor for ``project``."""
    return ProjectMediaIndex(project)


# EOF
