#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Site domain must come from configuration and never from a literal.

WHAT THIS LOCKS, and why it is worth a test file.

Production was measured on 2026-08-18 holding ``Site(id=1).domain ==
"127.0.0.1:8000"``. Every check anyone ran reported success -- the OAuth env
vars were set in ``.env.prod`` AND in the running process, both ``SocialApp``
rows existed with credentials populated -- so nothing pointed at the one value
that was wrong.

It was not a typo. ``setup_social_auth`` declared ``--domain`` with
``default="127.0.0.1:8000"``, and that command's own documented usage is
``python manage.py setup_social_auth`` with no flags. The INVITED invocation
wrote a development host onto whatever database it was aimed at.

The damage is invisible at the point of failure, which is why a regression test
is the right mechanism rather than a comment. ``SITE_ID`` pins allauth and
Django to that row, so it is the host used to build OAuth callback URLs and the
links inside confirmation and password-reset email. Nothing raises. The site
serves, the mail sends, and the URLs point at the recipient's own machine.

So these tests assert the SHAPE of the configuration, not an outcome: a run that
happens to have the right domain is indistinguishable from a codebase that
cannot get it wrong.
"""

import contextlib
import pathlib
from functools import partial

import pytest
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SETUP_SOCIAL_AUTH = (
    REPO_ROOT / "apps/infra/auth_app/management/commands/setup_social_auth.py"
)
SETTINGS_AUTH = REPO_ROOT / "config/settings/settings_auth.py"

#: The value production was actually found holding.
DEV_HOST = "127.0.0.1:8000"

#: The refusal must name this, or the operator is told what broke and not what
#: to do about it.
ENV_VAR = "SCITEX_HUB_SITE_DOMAIN"


def _argparse_defaults(source):
    """Only the ``default=`` lines, so prose about the bug cannot match."""
    return "\n".join(
        line for line in source.splitlines() if line.strip().startswith("default=")
    )


@pytest.fixture
def configured_domain(settings):
    """A deployment that knows its own domain."""
    settings.SITE_DOMAIN = "scitex.ai"
    settings.SITE_NAME = "SciTeX"
    return settings


@pytest.fixture
def unconfigured_domain(settings):
    """A deployment that does not, where guessing is the defect."""
    settings.SITE_DOMAIN = ""
    return settings


@pytest.fixture
def stale_site(settings):
    """The row as production was actually found: a development host."""
    Site.objects.update_or_create(
        id=settings.SITE_ID, defaults={"domain": DEV_HOST, "name": "dev"}
    )
    return settings


def test_setup_social_auth_still_declares_the_domain_flag():
    # Arrange
    source = SETUP_SOCIAL_AUTH.read_text()

    # Act
    declares_flag = '"--domain"' in source

    # Assert
    assert declares_flag, "the flag was renamed; update the guard below too"


def test_setup_social_auth_does_not_default_the_domain_to_a_dev_host():
    """The exact defect. FAILS on the pre-fix code, which is the point."""
    # Arrange
    source = SETUP_SOCIAL_AUTH.read_text()

    # Act
    defaults = _argparse_defaults(source)

    # Assert
    assert DEV_HOST not in defaults, (
        "setup_social_auth is defaulting --domain to a development host again. "
        "That default is how production's Site row became 127.0.0.1:8000: the "
        "command's documented usage omits the flag, so the default IS the value "
        "operators get. Read the domain from settings.SITE_DOMAIN "
        "($SCITEX_HUB_SITE_DOMAIN) and refuse when it is unset."
    )


def test_setup_social_auth_refuses_and_names_the_env_var(unconfigured_domain):
    """Refusing is the behaviour; naming the variable is half of it."""
    # Arrange
    run = partial(call_command, "setup_social_auth")

    # Act
    refusal = pytest.raises(CommandError, match=ENV_VAR)

    # Assert
    with refusal:
        run()


def test_sync_site_domain_refuses_and_names_the_env_var(unconfigured_domain):
    # Arrange
    run = partial(call_command, "sync_site_domain")

    # Act
    refusal = pytest.raises(CommandError, match=ENV_VAR)

    # Assert
    with refusal:
        run()


def test_sync_site_domain_replaces_a_stale_domain(configured_domain, stale_site):
    # Arrange
    site_id = configured_domain.SITE_ID

    # Act
    call_command("sync_site_domain")

    # Assert
    assert Site.objects.get(id=site_id).domain == "scitex.ai"


def test_sync_site_domain_applies_the_configured_name(configured_domain, stale_site):
    # Arrange
    site_id = configured_domain.SITE_ID

    # Act
    call_command("sync_site_domain")

    # Assert
    assert Site.objects.get(id=site_id).name == "SciTeX"


def test_sync_site_domain_keeps_exactly_one_row(configured_domain):
    """It runs on every boot, so a second run must not create a second row."""
    # Arrange
    call_command("sync_site_domain")

    # Act
    call_command("sync_site_domain")

    # Assert
    assert Site.objects.filter(id=configured_domain.SITE_ID).count() == 1


def test_sync_site_domain_is_idempotent(configured_domain):
    # Arrange
    call_command("sync_site_domain")

    # Act
    call_command("sync_site_domain")

    # Assert
    assert Site.objects.get(id=configured_domain.SITE_ID).domain == "scitex.ai"


def test_check_mode_reports_drift(configured_domain, stale_site):
    # Arrange
    run = partial(call_command, "sync_site_domain", "--check")

    # Act
    drift = pytest.raises(CommandError)

    # Assert
    with drift:
        run()


def test_check_mode_does_not_mutate_the_row(configured_domain, stale_site):
    """``--check`` is for asking, not fixing.

    The raise itself is asserted by :func:`test_check_mode_reports_drift`; here
    it is suppressed so this test carries exactly one assertion, about the row.
    """
    # Arrange
    with contextlib.suppress(CommandError):
        call_command("sync_site_domain", "--check")

    # Act
    stored = Site.objects.get(id=configured_domain.SITE_ID).domain

    # Assert
    assert stored == DEV_HOST


def test_settings_reads_the_site_domain_env_var():
    # Arrange
    source = SETTINGS_AUTH.read_text()

    # Act
    reads_env_var = ENV_VAR in source

    # Assert
    assert reads_env_var


def test_site_domain_setting_has_no_built_in_default():
    """A default that is right in dev and wrong in prod is the same defect."""
    # Arrange
    source = SETTINGS_AUTH.read_text()

    # Act
    getenv_lines = [
        line
        for line in source.splitlines()
        if ENV_VAR in line and "os.getenv" in line
    ]

    # Assert
    assert all('""' in line for line in getenv_lines), (
        "SITE_DOMAIN must fall back to empty so the commands can refuse; "
        f"got: {getenv_lines}"
    )
