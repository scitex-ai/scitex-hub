"""Actual PostgreSQL guards for an absent or populated retired Scholar table."""

import importlib
import json
from uuid import uuid4

import pytest
from django.db import connection
from django.db.migrations.state import ProjectState
from django.test import TestCase


@pytest.mark.guards(
    defect="Retiring SearchFilter deleted historical rows and failed when its table was already absent."
)
class SearchFilterRetirementTest(TestCase):
    def retire(self, populated):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        schema = "retirement_guard_" + uuid4().hex[:16]
        quoted = connection.ops.quote_name(schema)
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA " + quoted)
            cursor.execute("SET LOCAL search_path TO " + quoted)
        initial = importlib.import_module(
            "apps.workspace.scholar_app.migrations.0001_initial"
        )
        before = ProjectState()
        create = next(
            operation
            for operation in initial.Migration.operations
            if getattr(operation, "name", None) == "SearchFilter"
        )
        create.state_forwards("scholar_app", before)
        model = before.apps.get_model("scholar_app", "SearchFilter")
        identifier = uuid4()
        if populated:
            with connection.schema_editor(atomic=False) as editor:
                editor.create_model(model)
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO "scholar_app_searchfilter" '
                    "(id,name,filter_type,description,configuration,is_active,created_at,updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                    [
                        identifier,
                        "preserved fixture",
                        "topic",
                        "owned test record",
                        json.dumps({"retain": True}),
                        True,
                    ],
                )
        retirement = importlib.import_module(
            "apps.workspace.scholar_app.migrations.0020_delete_searchfilter"
        ).Migration("0020_delete_searchfilter", "scholar_app")
        with connection.schema_editor(atomic=False) as editor:
            after = retirement.apply(before, editor)
        self.assertNotIn(("scholar_app", "searchfilter"), after.models)
        if populated:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT name,configuration FROM "scholar_app_searchfilter" WHERE id=%s',
                    [identifier],
                )
                row = cursor.fetchone()
            self.assertEqual(row[0], "preserved fixture")
            self.assertEqual(
                json.loads(row[1]) if isinstance(row[1], str) else row[1],
                {"retain": True},
            )
        else:
            self.assertNotIn(
                "scholar_app_searchfilter", connection.introspection.table_names()
            )

    def test_absent_legacy_table_retires_without_a_phantom_table(self):
        self.retire(populated=False)

    def test_populated_legacy_table_and_payload_survive_model_retirement(self):
        self.retire(populated=True)
