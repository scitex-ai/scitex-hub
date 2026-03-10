"""
DataStore CRUD engine.

Provides structured read/write access to AppData records for a specific
(app_name, schema_name) namespace. Filter kwargs are mapped to JSONField
lookups (data__<field>__<lookup>) and, where indexed columns exist, to
the faster idx_* columns instead.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.infra.platform_app.models.app_data import AppData

from .schema import DatastoreSchema


class DatastoreEngine:
    """
    Core CRUD engine scoped to an (app_name, schema_name) pair.

    Args:
        app_name: The name of the plugin app (e.g. "lab_notebook").
        schema_name: The schema within that app (e.g. "entry").
        schema: Optional DatastoreSchema for index-aware filtering.
    """

    def __init__(
        self,
        app_name: str,
        schema_name: str,
        schema: Optional[DatastoreSchema] = None,
    ):
        self.app_name = app_name
        self.schema_name = schema_name
        self.schema = schema

    # ------------------------------------------------------------------
    # Scoped base queryset
    # ------------------------------------------------------------------

    def _base_qs(self) -> QuerySet:
        return AppData.objects.filter(
            app_name=self.app_name, schema_name=self.schema_name
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, project, owner, data: Dict[str, Any]) -> AppData:
        """Create and save a new AppData record. Returns the saved instance."""
        record = AppData(
            app_name=self.app_name,
            schema_name=self.schema_name,
            project=project,
            owner=owner,
            data=data,
        )
        self._populate_index_columns(record, data)
        record.save()
        return record

    def get(self, pk: Union[str, UUID]) -> AppData:
        """Retrieve a single record by primary key. Raises AppData.DoesNotExist on miss."""
        return self._base_qs().get(pk=pk)

    def filter(
        self,
        project,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> QuerySet:
        """
        Filter records for *project*. Extra kwargs are field-level filters.

        Supported kwargs:
            field_name=value          → exact match
            field_name__gte=value     → greater-than-or-equal
            field_name__lte=value
            field_name__contains=value
            field_name__icontains=value
            field_name__in=[...]

        Indexed columns are used transparently when available.
        """
        qs = self._base_qs().filter(project=project)
        qs = self._apply_field_filters(qs, kwargs)

        if order_by:
            qs = qs.order_by(order_by)
        if offset:
            qs = qs[offset:]
        if limit:
            qs = qs[:limit]

        return qs

    def update(self, pk: Union[str, UUID], data: Dict[str, Any]) -> AppData:
        """
        Overwrite the data field of record *pk* with *data*.

        Merges into existing data (shallow merge). Returns the updated record.
        """
        record = self.get(pk)
        record.data.update(data)
        self._populate_index_columns(record, record.data)
        record.save()
        return record

    def upsert(
        self,
        project,
        owner,
        unique_field: str,
        unique_value: Any,
        data: Dict[str, Any],
    ) -> AppData:
        """
        Create-or-update based on a unique field value within the project.

        Looks for an existing record where data[unique_field] == unique_value.
        If found, merges *data* into it. Otherwise, creates a new record.
        """
        index_col = self.schema.get_index_column(unique_field) if self.schema else None

        if index_col:
            lookup = {index_col: unique_value, "project": project}
        else:
            lookup = {f"data__{unique_field}": unique_value, "project": project}

        qs = self._base_qs().filter(**lookup)
        record = qs.first()

        if record is None:
            merged = {unique_field: unique_value, **data}
            return self.create(project=project, owner=owner, data=merged)

        record.data.update(data)
        record.data[unique_field] = unique_value
        self._populate_index_columns(record, record.data)
        record.save()
        return record

    def delete(self, pk: Union[str, UUID]) -> bool:
        """
        Delete record by primary key.

        Returns True if deleted, False if the record did not exist.
        """
        deleted_count, _ = self._base_qs().filter(pk=pk).delete()
        return deleted_count > 0

    def bulk_create(self, project, owner, items: List[Dict[str, Any]]) -> List[AppData]:
        """Create multiple records in a single database round-trip."""
        records = []
        for data in items:
            record = AppData(
                app_name=self.app_name,
                schema_name=self.schema_name,
                project=project,
                owner=owner,
                data=data,
            )
            self._populate_index_columns(record, data)
            records.append(record)

        return AppData.objects.bulk_create(records)

    def count(self, project, **kwargs: Any) -> int:
        """Return the count of records for *project* matching optional kwargs."""
        qs = self._base_qs().filter(project=project)
        qs = self._apply_field_filters(qs, kwargs)
        return qs.count()

    def search(self, project, query: str, fields: List[str]) -> QuerySet:
        """
        Full-text search across the listed JSON fields using icontains.

        Each field in *fields* is searched independently; results are OR-combined.
        """
        qs = self._base_qs().filter(project=project)

        if not fields or not query:
            return qs.none()

        q = Q()
        for field in fields:
            q |= Q(**{f"data__{field}__icontains": query})

        return qs.filter(q)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_field_filters(self, qs: QuerySet, kwargs: Dict[str, Any]) -> QuerySet:
        """
        Translate user-facing field kwargs into ORM lookups.

        For each kwarg key of the form 'field_name__lookup' or 'field_name',
        we check whether field_name has an indexed column. If yes, the indexed
        column is queried directly. Otherwise we fall through to a JSONField
        data__ lookup.
        """
        for key, value in kwargs.items():
            parts = key.split("__", 1)
            field_name = parts[0]
            lookup_suffix = parts[1] if len(parts) == 2 else None

            index_col = (
                self.schema.get_index_column(field_name) if self.schema else None
            )

            if index_col:
                orm_key = (
                    f"{index_col}__{lookup_suffix}" if lookup_suffix else index_col
                )
            else:
                orm_key = (
                    f"data__{field_name}__{lookup_suffix}"
                    if lookup_suffix
                    else f"data__{field_name}"
                )

            qs = qs.filter(**{orm_key: value})

        return qs

    def _populate_index_columns(self, record: AppData, data: Dict[str, Any]) -> None:
        """Copy indexed field values from data dict into the idx_* columns."""
        if self.schema is None:
            return

        for field_name, col_name in self.schema.index_map.items():
            value = data.get(field_name)
            setattr(record, col_name, value)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def get_engine(
    app_name: str,
    schema_name: str,
    schema: Optional[DatastoreSchema] = None,
) -> DatastoreEngine:
    """Return a DatastoreEngine for the given app/schema pair."""
    return DatastoreEngine(app_name=app_name, schema_name=schema_name, schema=schema)
