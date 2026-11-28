"""PostgreSQL controls for retaining retired visitor records and metrics."""

import importlib
from uuid import uuid4

import pytest
from django.db import connection, models
from django.db.migrations.state import ModelState, ProjectState
from django.test import TestCase


@pytest.mark.guards(
    defect="Retiring visitor features deleted historical allocation rows and metric values."
)
class RetiredVisitorStorageTest(TestCase):
    def owned_schema(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        schema = connection.ops.quote_name("retired_guard_" + uuid4().hex[:16])
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA " + schema)
            cursor.execute("SET LOCAL search_path TO " + schema)

    def apply_retirement(self, before, module, app):
        migration = importlib.import_module(module).Migration("retirement_guard", app)
        with connection.schema_editor(atomic=False) as editor:
            return migration.apply(before, editor)

    def test_retired_allocation_rows_survive_model_state_retirement(self):
        self.owned_schema()
        before = ProjectState()
        before.add_model(
            ModelState(
                "project_app",
                "VisitorAllocation",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("marker", models.TextField()),
                ],
            )
        )
        legacy = before.apps.get_model("project_app", "VisitorAllocation")
        with connection.schema_editor(atomic=False) as editor:
            editor.create_model(legacy)
        legacy.objects.create(marker="retained owned fixture")
        after = self.apply_retirement(
            before,
            "apps.infra.project_app.migrations.0042_delete_visitorallocation",
            "project_app",
        )
        self.assertNotIn(("project_app", "visitorallocation"), after.models)
        with connection.cursor() as cursor:
            cursor.execute("SELECT marker FROM project_app_visitorallocation")
            self.assertEqual(cursor.fetchall(), [("retained owned fixture",)])

    def test_historical_metrics_survive_and_new_orm_inserts_still_work(self):
        self.owned_schema()
        historical = importlib.import_module(
            "apps.infra.public_app.migrations.0007_servermetrics_visitor_pool_allocated_and_more"
        )
        fields = [("id", models.AutoField(primary_key=True))]
        fields += [
            (operation.name, operation.field.clone())
            for operation in historical.Migration.operations
        ]
        before = ProjectState()
        before.add_model(ModelState("public_app", "ServerMetrics", fields))
        legacy = before.apps.get_model("public_app", "ServerMetrics")
        with connection.schema_editor(atomic=False) as editor:
            editor.create_model(legacy)
        row = legacy.objects.create(visitor_pool_allocated=2, visitor_pool_total=4)
        after = self.apply_retirement(
            before,
            "apps.infra.public_app.migrations.0016_remove_servermetrics_visitor_pool_allocated_and_more",
            "public_app",
        )
        current = after.apps.get_model("public_app", "ServerMetrics")
        new_row = current.objects.create()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,visitor_pool_allocated,visitor_pool_total FROM public_app_servermetrics ORDER BY id"
            )
            self.assertEqual(
                cursor.fetchall(), [(row.pk, 2, 4), (new_row.pk, None, None)]
            )
