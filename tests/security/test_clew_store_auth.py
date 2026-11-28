"""Real API-key and unavailable-configuration checks against the leaf mount."""

from datetime import timedelta

from django.test import Client, override_settings
from django.utils import timezone

from apps.infra.accounts_app.models.api_key import APIKey

from ._clew_store_fixture import ClewStoreFixture


class ClewStoreAuthTest(ClewStoreFixture):
    def test_api_key_uses_its_owner_and_refuses_expired_or_revoked_keys(self):
        key, credential = APIKey.create_key(
            self.alice, "synthetic-clew-read", scopes=["api"]
        )
        client = Client(HTTP_AUTHORIZATION="Bearer " + credential)
        response = client.get(
            "/apps/clew/api/runs/", {"project": "clew-alice/paper-scitex-clew"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("alice-evidence", response.content.decode())
        self.assertNotIn("bob-evidence", response.content.decode())
        foreign = client.get(
            "/apps/clew/api/runs/", {"project": "clew-bob/paper-scitex-clew"}
        )
        self.assertEqual(foreign.status_code, 404)
        key.is_active = False
        key.save(update_fields=["is_active"])
        self.assertEqual(client.get("/apps/clew/api/runs/").status_code, 401)
        key.is_active, key.expires_at = True, timezone.now() - timedelta(seconds=1)
        key.save(update_fields=["is_active", "expires_at"])
        self.assertEqual(client.get("/apps/clew/api/runs/").status_code, 401)

    def test_keys_without_the_existing_api_permission_are_refused(self):
        for scopes in ([], ["publish"], ["mcp"], ["read:projects"]):
            with self.subTest(scopes=scopes):
                _, credential = APIKey.create_key(
                    self.alice, "synthetic-limited-key", scopes=scopes
                )
                response = Client(HTTP_AUTHORIZATION="Bearer " + credential).get(
                    "/apps/clew/api/runs/", {"project": "clew-alice/paper-scitex-clew"}
                )
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("alice-evidence", response.content.decode())

    def test_invalid_operator_configuration_never_exposes_credentials(self):
        for configuration in (
            "{",
            [],
            {str(self.alice.pk): []},
            {
                str(self.alice.pk): {
                    "tenant_id": "invalid",
                    "dsn": "DO_NOT_ECHO_CREDENTIAL",
                    "projects": {str(self.paper.pk): "scope"},
                }
            },
        ):
            with self.subTest(configuration_type=type(configuration).__name__):
                with override_settings(SCITEX_STORE_TENANT_SECRETS=configuration):
                    response = self.get("stats/")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("DO_NOT_ECHO_CREDENTIAL", response.content.decode())
                self.assertNotIn("total_runs", response.json())
