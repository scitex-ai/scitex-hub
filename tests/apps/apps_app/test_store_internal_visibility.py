#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The store listing hides "internal" (staff-only / WIP) apps from non-staff.

Card compass-impl-app-visibility-gate-20260910 (P0, beta gate). Measured
2026-09-10, anonymous GET /apps/store/ listed Cards + Storage (both declared
"internal" in their manifest.json) plus the staff-only "Owner Hub" chrome — a
public exposure, not "internal only".

Root cause: seed_apps.py stamped EVERY builtin's AppsModule.visibility to
"public" (ignoring the manifest), so the store's Q(visibility="public") filter
served the internal apps to everyone. The fix reads the manifest's visibility
(registry.py:349, default "public") and adds "internal" to the staff-only
branch of browse_context.

These tests exercise browse_context directly (the single place that shapes the
store query) against the real test DB — no mocks.
"""

from pathlib import Path

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.workspace.apps_app.models import AppsModule
from apps.workspace.apps_app.views import helpers as apps_helpers
from apps.workspace.apps_app.views.helpers import browse_context, can_view_module


def _request(user):
    req = RequestFactory().get("/apps/store/")
    req.user = user
    return req


class StoreInternalVisibilityTest(TestCase):
    def setUp(self):
        self.pub = AppsModule.objects.create(
            module_name="storevis-pub", category="other", visibility="public"
        )
        self.internal = AppsModule.objects.create(
            module_name="storevis-internal", category="other", visibility="internal"
        )
        self.private = AppsModule.objects.create(
            module_name="storevis-private",
            category="other",
            visibility="private",
            author=self.pub.author if self.pub.author else None,
        )
        self.anon = AnonymousUser()
        self.staff = User.objects.create_user(username="storevis-staff", is_staff=True)
        self.regular = User.objects.create_user(username="storevis-user")

    def _names(self, user):
        ctx = browse_context(_request(user))
        return {m["app"].module_name for m in ctx["modules"]}

    def test_anonymous_sees_public_not_internal(self):
        names = self._names(self.anon)
        assert "storevis-pub" in names, "a public app must show for anonymous users"
        assert "storevis-internal" not in names, (
            "an internal (staff-only) app leaked into the anonymous store listing"
        )
        assert "storevis-private" not in names

    def test_regular_user_sees_public_not_internal(self):
        names = self._names(self.regular)
        assert "storevis-pub" in names
        assert "storevis-internal" not in names, (
            "an internal app is staff-only; a non-staff authenticated user must "
            "not see it"
        )

    def test_staff_sees_internal(self):
        names = self._names(self.staff)
        assert "storevis-internal" in names, (
            "staff must see internal apps (that is the operator view)"
        )
        assert "storevis-pub" in names


class TestOwnerHubChromeStaffOnly:
    """The staff-only 'Owner Hub' card link must be gated on user.is_staff.
    'Disable' was already inside the {% if user.is_authenticated %} block;
    'Owner Hub' rendered for ANY app with an author — and the seed stamps
    author on every builtin — so it leaked to everyone. It is now staff-only.

    Source-scan (no DB, no custom template tags): the 'Owner Hub' anchor's
    guarding {% if %} must include user.is_staff. Rendering the whole card
    here would pull in the module_icon tag and full card context for a
    one-line guard — the scan is the tighter, more honest assertion.
    """

    CARD = (
        Path(__file__).resolve().parents[3]
        / "apps/workspace/apps_app/templates/apps_app/partials/module_card.html"
    )

    @staticmethod
    def _owner_hub_guard(src: str) -> str:
        """The {% if ... %} line that guards the 'Owner Hub' anchor — the
        nearest such line above the text (skipping the is_dev {% if %} that
        sits inside the anchor's own href)."""
        idx = src.find("Owner Hub")
        assert idx != -1, "the 'Owner Hub' anchor is gone from module_card.html"
        lines = src[:idx].splitlines()
        for line in reversed(lines):
            s = line.strip()
            # The guard is the {% if %} opening tag itself (a line that STARTS
            # with it) — not the <a href="{% if is_dev %}..." line, which also
            # contains "mod_item.app.author" inside the URL.
            if s.startswith("{% if") and "mod_item.app.author" in s:
                return s
        return ""

    def test_owner_hub_link_is_gated_on_staff(self):
        guard = self._owner_hub_guard(self.CARD.read_text(encoding="utf-8"))
        assert guard, "the 'Owner Hub' anchor's author guard {% if %} is missing"
        assert "user.is_staff" in guard, (
            "the 'Owner Hub' staff-only link must be guarded by user.is_staff; "
            f"current guard: {guard.strip()!r}"
        )

    def test_owner_hub_not_gated_only_on_authenticated(self):
        # Regression guard: gating on is_authenticated alone would still show
        # 'Owner Hub' to every logged-in non-staff user (the P0 defect).
        guard = self._owner_hub_guard(self.CARD.read_text(encoding="utf-8"))
        assert guard and "is_staff" in guard, (
            f"'Owner Hub' guard must require staff (not just is_authenticated): "
            f"{guard.strip()!r}"
        )


class SeedRespectsManifestVisibilityTest(TestCase):
    """ensure_builtin_modules must seed visibility FROM the manifest, not
    hardcode "public" — the regression that exposed the internal apps."""

    def test_internal_manifest_module_is_seeded_internal(self):
        from apps.infra.workspace_app import registry
        from apps.workspace.apps_app.management.commands.seed_apps import (
            ensure_builtin_modules,
        )

        # Register a fake builtin whose manifest declares "internal". The
        # partial_template must NOT start with apps_app/user_apps/ — that prefix
        # is the runtime-registration signature ensure_builtin_modules skips.
        cfg = registry.ModuleConfig(
            name="storevis-seed-internal",
            label="Seed Internal",
            app_name="apps_app",
            partial_template="storevis/seed_internal_partial.html",
        )
        cfg.visibility = "internal"
        registry.register_module(cfg)
        try:
            # Arrange: pre-existing row stamped public (the old bug's residue).
            AppsModule.objects.create(
                module_name="storevis-seed-internal",
                category="other",
                visibility="public",
                is_builtin=True,
            )
            # Act: re-run the idempotent seed.
            ensure_builtin_modules()
            # Assert: the manifest's "internal" won — the stale "public" row
            # was corrected, so the store query (Q(visibility="public"))
            # no longer serves it.
            row = AppsModule.objects.get(module_name="storevis-seed-internal")
            assert row.visibility == "internal", (
                f"seed stamped visibility={row.visibility!r}; the manifest "
                "declares 'internal' and must win (card app-visibility-gate)"
            )
        finally:
            registry.unregister_module("storevis-seed-internal")


class RuntimeHelperResyncsDriftedVisibilityTest(TestCase):
    """The runtime ensure_builtin_modules (helpers.py) must RESYNC a builtin
    row whose stored visibility drifted from the manifest SSoT — the exact
    regression the seed-only test above does NOT cover.

    The old fast path (`registered_names <= existing_names -> return`) never
    re-synced existing rows, so a Cards/Storage row seeded 'public' before its
    manifest flipped to 'internal' leaked to the anonymous App Store forever
    (hub-store-tiles-cards-internal-visibility-regression-20260914).
    """

    def setUp(self):
        # The helper caches its "done" state in a module global; reset it so a
        # fresh process-simulated run executes the resync logic.
        apps_helpers._builtins_ensured = False

    def tearDown(self):
        apps_helpers._builtins_ensured = False
        # Drop the synthetic module so other tests in the file see a clean registry.
        from apps.infra.workspace_app import registry
        try:
            registry.unregister_module("storevis-drift-internal")
        except Exception:
            pass

    def test_stale_public_row_for_internal_manifest_is_resynced(self):
        from apps.infra.workspace_app import registry

        cfg = registry.ModuleConfig(
            name="storevis-drift-internal",
            label="Drift Internal",
            app_name="apps_app",
            partial_template="storevis/drift_internal_partial.html",
        )
        cfg.visibility = "internal"
        registry.register_module(cfg)
        try:
            # Arrange: a builtin row present but stamped 'public' (the drift).
            row = AppsModule.objects.create(
                module_name="storevis-drift-internal",
                category="other",
                visibility="public",
                is_builtin=True,
            )
            assert row.visibility == "public"  # the pre-fix stale state
            # Act: the runtime helper (not the seeder directly) must correct it.
            apps_helpers.ensure_builtin_modules()
            # Assert: manifest 'internal' won; the store's public filter hides it.
            row.refresh_from_db()
            assert row.visibility == "internal", (
                f"runtime helper left drifted row at {row.visibility!r}; the "
                "manifest SSoT ('internal') must resync it, else the anonymous "
                "App Store leaks the app"
            )
            # And the store listing agrees.
            anon = AnonymousUser()
            names = {m["app"].module_name for m in browse_context(_request(anon))["modules"]}
            assert "storevis-drift-internal" not in names, (
                "a resynced internal app must not appear in the anonymous store"
            )
        finally:
            registry.unregister_module("storevis-drift-internal")
            AppsModule.objects.filter(module_name="storevis-drift-internal").delete()


class CanViewModuleBuiltinDoesNotBypassInternalTest(TestCase):
    """can_view_module must NOT grant access to an 'internal' builtin via the
    is_builtin short-circuit — the secondary gap that would leak an internal
    app on the detail/open path even with a correctly-marked DB row.
    """

    def setUp(self):
        from apps.infra.workspace_app import registry

        self._cfgs = []
        # A staff user and an anonymous + regular user.
        self.staff = User.objects.create_user(username="cvm-staff", is_staff=True)
        self.regular = User.objects.create_user(username="cvm-user")
        self.anon = AnonymousUser()

    def _mk(self, name, visibility, builtin=True):
        mod = AppsModule.objects.create(
            module_name=name,
            category="other",
            visibility=visibility,
            is_builtin=builtin,
        )
        return mod

    def test_internal_builtin_hidden_from_anonymous(self):
        mod = self._mk("cvm-internal-builtin", "internal")
        assert can_view_module(self.anon, mod) is False, (
            "an internal builtin must be hidden from anonymous users; "
            "is_builtin must not bypass the internal release-channel gate"
        )

    def test_internal_builtin_hidden_from_regular_user(self):
        from django.test import override_settings

        mod = self._mk("cvm-internal-builtin2", "internal")
        # Pin the deployment flag OFF so this is deterministic: a regular
        # (non-staff) user must NOT see internal apps on a non-RELEASED
        # deployment. (Dev defaults the flag true — every authenticated user
        # sees internal apps — so without the override this would pass for the
        # wrong reason.)
        with override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=False):
            assert can_view_module(self.regular, mod) is False, (
                "an internal builtin is staff/RELEASED-only; a regular "
                "authenticated user must not open it when the flag is unset"
            )

    def test_internal_builtin_visible_to_staff(self):
        mod = self._mk("cvm-internal-builtin3", "internal")
        assert can_view_module(self.staff, mod) is True, (
            "staff (operators) must always see internal apps"
        )

    def test_public_builtin_still_visible_to_anonymous(self):
        # Guard against over-tightening: a PUBLIC builtin must still be
        # visible to everyone (the normal case — writer/scholar/figrecipe).
        mod = self._mk("cvm-public-builtin", "public")
        assert can_view_module(self.anon, mod) is True
        assert can_view_module(self.regular, mod) is True
