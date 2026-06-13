"""Tests for Agentic Journal workspace app."""

from django.test import TestCase

from apps.infra.workspace_app.test_mixin import ModuleTestMixin


class AgenticJournalModuleTest(ModuleTestMixin, TestCase):
    """Registry integration tests for Agentic Journal (auto-validated by ModuleTestMixin)."""

    module_name = "scitex_agentic_journal_hub"


class AgenticJournalContextTest(TestCase):
    """Unit tests for Agentic Journal context builder."""

    def test_context_has_required_keys(self):
        """Context builder returns all expected keys."""
        from django.test import RequestFactory
        from django.contrib.auth.models import User

        from apps.scitex_agentic_journal_hub_app.views import (
            build_scitex_agentic_journal_hub_app_context,
        )

        factory = RequestFactory()
        request = factory.get("/scitex_agentic_journal_hub_app/")
        request.user = User(username="testuser")

        ctx = build_scitex_agentic_journal_hub_app_context(request)
        self.assertIn("app_name", ctx)
        self.assertEqual(ctx["app_name"], "Agentic Journal")
        self.assertIn("app_description", ctx)
        self.assertIn("features", ctx)
        self.assertIsInstance(ctx["features"], list)


# EOF
