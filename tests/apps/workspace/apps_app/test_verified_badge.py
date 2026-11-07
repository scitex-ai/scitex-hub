"""Verified badge: bound to the certification pin, relaxed off-production."""

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from apps.workspace.apps_app.models import AppsModule, ModuleVersion


@pytest.fixture
def author(db):
    return User.objects.create_user(username="badge_publisher")


@pytest.fixture
def module(author):
    return AppsModule.objects.create(
        module_name="badge-probe",
        author=author,
        label="Badge Probe",
        category="tools",
        is_verified=True,
    )


def _release(module, version):
    return ModuleVersion.objects.create(module=module, version=version)


def test_unverified_never_shows_badge(author):
    mod = AppsModule.objects.create(
        module_name="unverified-probe",
        author=author,
        label="Unverified",
        category="tools",
        is_verified=False,
        pinned_version="0.1.0",
    )
    _release(mod, "0.1.0")
    with override_settings(SCITEX_ENV="production"):
        assert mod.shows_verified_badge() is False


def test_relaxed_mode_shows_badge_on_flag_alone(module):
    # No pin, no versions: develop/dev-mode never slows for the badge.
    with override_settings(SCITEX_ENV="development"):
        assert module.shows_verified_badge() is True


def test_strict_mode_shows_badge_for_pinned_version(module):
    module.pinned_version = "0.2.0"
    module.save(update_fields=["pinned_version"])
    _release(module, "0.1.0")
    _release(module, "0.2.0")
    with override_settings(SCITEX_ENV="production"):
        assert module.shows_verified_badge() is True


def test_strict_mode_hides_badge_after_new_release(module):
    # Publisher ships 0.3.0 after 0.2.0 was certified: no badge until
    # re-certification moves the pin.
    module.pinned_version = "0.2.0"
    module.save(update_fields=["pinned_version"])
    _release(module, "0.2.0")
    _release(module, "0.3.0")
    with override_settings(SCITEX_ENV="production"):
        assert module.shows_verified_badge() is False


def test_strict_mode_hides_badge_without_pin(module):
    _release(module, "0.1.0")
    with override_settings(SCITEX_ENV="production"):
        assert module.shows_verified_badge() is False
