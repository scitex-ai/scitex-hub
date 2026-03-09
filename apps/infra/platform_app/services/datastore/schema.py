"""
DataStore schema parser.

Reads the datastore section of a manifest.yaml and validates field types.
Also determines which fields map to indexed columns (idx_string_1/2, idx_integer_1/2).
"""

from typing import Any, Dict, List, Optional

ALLOWED_FIELD_TYPES = {
    "string",
    "text",
    "integer",
    "float",
    "boolean",
    "datetime",
    "date",
    "json",
    "file",
    "choice",
    "ref",
    "relation",
    "project_ref",
}

# Field types that can be promoted to indexed integer columns
INTEGER_INDEXABLE_TYPES = {"integer"}

# Field types that can be promoted to indexed string columns
STRING_INDEXABLE_TYPES = {"string", "choice", "ref"}

# Maximum number of indexed columns per type
MAX_STRING_INDEXES = 2
MAX_INTEGER_INDEXES = 2


class SchemaValidationError(ValueError):
    """Raised when a manifest schema definition is invalid."""


class DatastoreSchema:
    """Parsed and validated schema for a single datastore entry."""

    def __init__(self, schema_name: str, fields: Dict[str, Any]):
        self.schema_name = schema_name
        self.fields = fields
        # Maps field_name -> indexed column name (e.g. "idx_string_1")
        self.index_map: Dict[str, str] = {}
        self._build_index_map()

    def _build_index_map(self) -> None:
        """Assign indexed columns to fields that declare index=true."""
        string_count = 0
        integer_count = 0

        for field_name, field_def in self.fields.items():
            if not field_def.get("index", False):
                continue

            field_type = field_def.get("type", "string")

            if field_type in STRING_INDEXABLE_TYPES:
                if string_count < MAX_STRING_INDEXES:
                    string_count += 1
                    self.index_map[field_name] = f"idx_string_{string_count}"

            elif field_type in INTEGER_INDEXABLE_TYPES:
                if integer_count < MAX_INTEGER_INDEXES:
                    integer_count += 1
                    self.index_map[field_name] = f"idx_integer_{integer_count}"

    def get_index_column(self, field_name: str) -> Optional[str]:
        """Return the indexed column name for a field, or None."""
        return self.index_map.get(field_name)

    def field_names(self) -> List[str]:
        return list(self.fields.keys())

    def field_type(self, field_name: str) -> Optional[str]:
        field_def = self.fields.get(field_name)
        return field_def.get("type") if field_def else None


def parse_manifest_schema(
    manifest: Dict[str, Any], schema_name: str
) -> DatastoreSchema:
    """
    Parse a single schema from the datastore section of a manifest dict.

    Args:
        manifest: The full parsed manifest.yaml dict.
        schema_name: The name of the schema to parse.

    Returns:
        A validated DatastoreSchema instance.

    Raises:
        SchemaValidationError: If the schema is missing or has invalid field types.
    """
    datastore = manifest.get("datastore", {})
    if schema_name not in datastore:
        raise SchemaValidationError(
            f"Schema '{schema_name}' not found in manifest datastore section. "
            f"Available schemas: {list(datastore.keys())}"
        )

    schema_def = datastore[schema_name]
    fields = schema_def.get("fields", {})

    if not isinstance(fields, dict):
        raise SchemaValidationError(
            f"Schema '{schema_name}' fields must be a mapping, got {type(fields).__name__}."
        )

    _validate_fields(schema_name, fields)

    return DatastoreSchema(schema_name=schema_name, fields=fields)


def _validate_fields(schema_name: str, fields: Dict[str, Any]) -> None:
    """Validate all field definitions in a schema."""
    for field_name, field_def in fields.items():
        if not isinstance(field_def, dict):
            raise SchemaValidationError(
                f"Field '{field_name}' in schema '{schema_name}' must be a mapping."
            )

        field_type = field_def.get("type")
        if not field_type:
            raise SchemaValidationError(
                f"Field '{field_name}' in schema '{schema_name}' is missing 'type'."
            )

        if field_type not in ALLOWED_FIELD_TYPES:
            raise SchemaValidationError(
                f"Field '{field_name}' in schema '{schema_name}' has unsupported type "
                f"'{field_type}'. Allowed types: {sorted(ALLOWED_FIELD_TYPES)}."
            )
