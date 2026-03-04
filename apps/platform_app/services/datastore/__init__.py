"""
DataStore service — public API.

Usage example::

    from apps.platform_app.services.datastore import get_engine, DatastoreEngine
    from apps.platform_app.services.datastore import parse_manifest_schema
    from apps.platform_app.services.datastore import check_read, check_write

    engine = get_engine("my_app", "entry")
    record = engine.create(project=project, owner=request.user, data={"title": "Hello"})
"""

from .engine import DatastoreEngine, get_engine
from .permissions import (
    AccessMode,
    PermissionDeniedError,
    check_create,
    check_read,
    check_write,
)
from .schema import (
    ALLOWED_FIELD_TYPES,
    DatastoreSchema,
    SchemaValidationError,
    parse_manifest_schema,
)

__all__ = [
    # Engine
    "DatastoreEngine",
    "get_engine",
    # Schema
    "DatastoreSchema",
    "SchemaValidationError",
    "parse_manifest_schema",
    "ALLOWED_FIELD_TYPES",
    # Permissions
    "AccessMode",
    "PermissionDeniedError",
    "check_create",
    "check_read",
    "check_write",
]
