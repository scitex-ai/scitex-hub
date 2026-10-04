"""Retiring an unused model must preserve its historical table and rows."""

import importlib.util
from pathlib import Path

import pytest
from django.db import ConnectionHandler
from django.db.migrations.state import ProjectState


def _migration(name):
    root = Path(__file__).resolve().parents[5]
    source = root / "apps/workspace/scholar_app/migrations" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"retirement_{name}", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Migration(name, "scholar_app")


@pytest.mark.django_db(transaction=True)
def test_historical_filter_rows_survive_forward_and_reverse_retirement():
    initial = _migration("0001_initial")
    retirement = _migration("0020_retire_searchfilter_state_only")
    create_filter = next(
        operation for operation in initial.operations
        if getattr(operation, "name", None) == "SearchFilter"
    )
    before = ProjectState()
    create_filter.state_forwards("scholar_app", before)
    historical_model = before.apps.get_model("scholar_app", "SearchFilter")

    # A separately owned transient connection never touches the serving store.
    connections = ConnectionHandler({
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    })
    connection = connections["default"]
    try:
        with connection.schema_editor(atomic=False) as schema_editor:
            schema_editor.create_model(historical_model)
        row = historical_model(
            name="retained filter", filter_type="topic",
            configuration={"topic": "retained"},
        )
        fields = historical_model._meta.local_concrete_fields
        columns = ", ".join(connection.ops.quote_name(field.column) for field in fields)
        placeholders = ", ".join(["%s"] * len(fields))
        values = [
            field.get_db_prep_save(field.pre_save(row, add=True), connection)
            for field in fields
        ]
        table = connection.ops.quote_name(historical_model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values
            )
            cursor.execute(f"SELECT * FROM {table}")
            original_rows = cursor.fetchall()
        assert len(original_rows) == 1
        sql = []

        def record_sql(execute, statement, params, many, context):
            sql.append(statement)
            return execute(statement, params, many, context)

        with connection.schema_editor(atomic=False) as schema_editor:
            with connection.execute_wrapper(record_sql):
                after = retirement.apply(before.clone(), schema_editor)
        assert ("scholar_app", "searchfilter") not in after.models
        assert sql == []
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table}")
            assert cursor.fetchall() == original_rows

        with connection.schema_editor(atomic=False) as schema_editor:
            with connection.execute_wrapper(record_sql):
                restored = retirement.unapply(before.clone(), schema_editor)
        assert restored.models == before.models
        assert sql == []
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table}")
            assert cursor.fetchall() == original_rows
    finally:
        connections.close_all()
