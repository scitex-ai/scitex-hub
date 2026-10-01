"""Both SDK wizard prefixes retain the same login and leaf-view contracts."""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from scitex_sdk.creator import views


class SdkCreatorRouteCompatibilityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sdk-route-compatibility")

    def test_canonical_namespace_still_reverses_to_apps_new(self):
        self.assertEqual(reverse("scitex_sdk_creator:index"), "/apps/new/")

    def test_legacy_namespace_reverses_to_the_bookmarked_prefix(self):
        self.assertEqual(reverse("scitex_sdk_creator_legacy:index"), "/create-app/")

    def test_both_prefixes_mount_the_sdk_view(self):
        for prefix in ("/apps/new/", "/create-app/"):
            with self.subTest(prefix=prefix):
                self.assertIs(resolve(prefix).func.__wrapped__, views.index)

    def test_anonymous_get_and_post_are_gated_at_both_prefixes(self):
        for prefix in ("/apps/new/", "/create-app/"):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.client.get(prefix + "api/starters").status_code, 302)
                self.assertEqual(
                    self.client.post(
                        prefix + "api/validate-input",
                        data=json.dumps({"label": "Synthetic app"}),
                        content_type="application/json",
                    ).status_code,
                    302,
                )

    def test_signed_in_health_contract_agrees_at_both_prefixes(self):
        self.client.force_login(self.user)
        for prefix in ("/apps/new/", "/create-app/"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    self.client.get(prefix + "healthz").json(),
                    {"ok": True, "app": "scitex-sdk-creator"},
                )

    def test_signed_in_starters_contract_agrees_at_both_prefixes(self):
        self.client.force_login(self.user)
        canonical = self.client.get("/apps/new/api/starters")
        legacy = self.client.get("/create-app/api/starters")
        self.assertEqual(canonical.status_code, 200)
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(canonical.json(), legacy.json())
