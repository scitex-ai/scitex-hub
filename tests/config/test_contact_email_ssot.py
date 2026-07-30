#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every public @scitex.ai address comes from ``config/branding.py``.

Two halves, because there are two ways a use site can be wrong:

INJECTED sites (the normal case) read the address through the ``site_branding``
context processor or import it from ``config.branding``. Their failure mode is
not a stale address — it is an EMPTY one. A template naming ``{{ LEGAL_EMAIL }}``
that is rendered WITHOUT context processors emits ``href="mailto:"`` with nothing
after it: a legal page that looks finished and cannot be replied to. Reading the
template source cannot detect that, so the tests below FETCH each converted page
through the real URLconf and assert on the rendered bytes.

LITERAL sites cannot read Django context at all, for reasons that are not
stylistic:

  templates/500.html
      Django's default handler500 (``django.views.defaults.server_error``)
      renders WITHOUT context processors, and hub defines no handler500 of its
      own. That file also contains zero ``{{ VAR }}`` references of any kind —
      nobody has ever successfully used a context variable in it. A ``{{ }}``
      here would emit an EMPTY ``mailto:`` on the one page a stuck user needs.
  deployment/docker/common/nginx/error-pages/502.html
      Served BY NGINX, precisely when Django is down and cannot render anything.
  deployment/docker/Dockerfile.user-workspace
      A ``LABEL maintainer``, evaluated at image build with no Python at all.

So the duplication stays. What must NOT stay is silent DRIFT: the failure mode
this guards is a future "change the contact address" landing on the 20 injectable
sites and quietly skipping these three, leaving pages that look deliberate but
are stale. SSoT by ASSERTION where SSoT by injection is impossible.

The negative check asserts the file's @scitex.ai addresses are EXACTLY
{CONTACT_EMAIL} rather than "does not contain the old value". A test naming the
old literal would have to be edited on every future change and would pass
vacuously once that literal existed nowhere.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse

from config import branding
from config.context_processors import site_branding

# Files that must repeat the address because they cannot read Django context.
LITERAL_SITES = (
    "templates/500.html",
    "deployment/docker/common/nginx/error-pages/502.html",
    "deployment/docker/Dockerfile.user-workspace",
)

ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@scitex\.ai")

# Every address the SSoT owns. ywatanabe@scitex.ai is DELIBERATELY ABSENT — the
# operator ruled it their correct personal contact (2026-07-30), so it is not a
# branding constant and must not be folded into one.
SSOT_ADDRESS_NAMES = (
    "CONTACT_EMAIL",
    "LEGAL_EMAIL",
    "PRIVACY_EMAIL",
    "RECRUIT_EMAIL",
    "NOREPLY_EMAIL",
)

# Templates converted from a literal to a context variable. Each is rendered by
# a view that calls ``django.shortcuts.render(request, ...)``, which builds a
# RequestContext and therefore runs the context processors listed in
# settings_shared.TEMPLATES -- ``config.context_processors.site_branding`` among
# them. That is the whole reason the conversion is safe here and NOT safe in
# templates/500.html, which no such view renders.
#
#   apps/infra/public_app/views/legal.py:40  terms_of_use   -> terms
#   apps/infra/public_app/views/legal.py:35  privacy_policy -> privacy
#   apps/infra/public_app/views/legal.py:45  cookie_policy  -> cookies
#   apps/infra/public_app/views/pages.py:89  recruit        -> recruit
CONVERTED_TEMPLATES = (
    "apps/infra/public_app/templates/public_app/legal/terms_of_use.html",
    "apps/infra/public_app/templates/public_app/legal/privacy_policy.html",
    "apps/infra/public_app/templates/public_app/legal/cookie_policy.html",
    "apps/infra/public_app/templates/public_app/pages/recruit.html",
)

# (url name, the branding constant that page's address must equal).
CONVERTED_PAGES = (
    ("public_app:terms", "LEGAL_EMAIL"),
    ("public_app:privacy", "LEGAL_EMAIL"),
    ("public_app:cookies", "PRIVACY_EMAIL"),
    ("public_app:recruit", "RECRUIT_EMAIL"),
)

# ``{{ SOME_EMAIL }}``, however it is spaced. Used to discover which context
# variables a converted template actually depends on, rather than trusting a
# hand-maintained list to stay in step with the templates.
EMAIL_VAR_RE = re.compile(r"\{\{\s*([A-Z][A-Z0-9_]*EMAIL)\s*\}\}")

# What an unresolved context variable leaves behind: ``href="mailto:"``.
EMPTY_MAILTO = 'mailto:"'


def _read(rel):
    return (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", LITERAL_SITES)
def test_literal_site_file_is_readable(rel):
    """Anti-vacuity: a missing or empty file must fail, not read as compliant."""
    # Arrange
    minimum_bytes = 50

    # Act
    size = len(_read(rel))

    # Assert
    assert size > minimum_bytes, (
        f"{rel} read as {size} bytes. If it moved, update LITERAL_SITES — do not "
        "delete this check, or the assertions below would pass on an empty string."
    )


@pytest.mark.parametrize("rel", LITERAL_SITES)
def test_literal_site_carries_the_contact_address(rel):
    """The address a user is told to write to must be the real one."""
    # Arrange
    expected = branding.CONTACT_EMAIL

    # Act
    content = _read(rel)

    # Assert
    assert expected in content, (
        f"{rel} does not contain branding.CONTACT_EMAIL ({expected}). This file "
        "cannot read the context processor, so it must repeat the literal; when "
        "you change CONTACT_EMAIL you must edit this file in the same commit."
    )


@pytest.mark.parametrize("rel", LITERAL_SITES)
def test_literal_site_has_no_other_scitex_address(rel):
    """No stale sibling address may linger beside the current one."""
    # Arrange
    allowed = {branding.CONTACT_EMAIL}

    # Act
    found = set(ADDRESS_RE.findall(_read(rel)))

    # Assert
    assert found == allowed, (
        f"{rel} contains @scitex.ai addresses {sorted(found)}, expected exactly "
        f"{sorted(allowed)}. An address here that is not CONTACT_EMAIL has "
        "drifted — this file is invisible to the context processor, so nothing "
        "else would have caught it."
    )


@pytest.mark.parametrize("name", SSOT_ADDRESS_NAMES)
def test_ssot_address_is_built_from_the_shared_domain(name):
    """A domain move must be one edit, so no address may hardcode the domain."""
    # Arrange
    expected_suffix = "@" + branding.CONTACT_DOMAIN

    # Act
    actual = getattr(branding, name)

    # Assert
    assert actual.endswith(expected_suffix), (
        f"{name} ({actual}) does not end with {expected_suffix}; it should be "
        "composed from CONTACT_DOMAIN so the domain stays single-sourced."
    )


# ---------------------------------------------------------------------------
# Injected sites: the template no longer holds the address at all
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rel", CONVERTED_TEMPLATES)
def test_converted_template_file_is_readable(rel):
    """Anti-vacuity: ``findall`` over an empty string also returns []."""
    # Arrange
    minimum_bytes = 50

    # Act
    size = len(_read(rel))

    # Assert
    assert size > minimum_bytes, (
        f"{rel} read as {size} bytes. If it moved, update CONVERTED_TEMPLATES — "
        "do not delete this check, or the assertions below would pass on an empty "
        "string and a truncated template would read as perfectly converted."
    )


@pytest.mark.parametrize("rel", CONVERTED_TEMPLATES)
def test_converted_template_hardcodes_no_address(rel):
    """A re-hardcoded address would drift the moment the constant changes."""
    # Arrange
    expected = []

    # Act
    found = sorted(set(ADDRESS_RE.findall(_read(rel))))

    # Assert
    assert found == expected, (
        f"{rel} hardcodes {found}. This template is rendered with context "
        "processors, so it must use the site_branding variable (e.g. "
        "{{ LEGAL_EMAIL }}) instead of a literal."
    )


@pytest.mark.parametrize("rel", CONVERTED_TEMPLATES)
def test_converted_template_references_an_email_context_var(rel):
    """Anti-vacuity for the export check: an unconverted template uses none."""
    # Arrange
    pattern = EMAIL_VAR_RE.pattern

    # Act
    used = sorted(set(EMAIL_VAR_RE.findall(_read(rel))))

    # Assert
    assert used, (
        f"{rel} matches no {pattern!r}. Either the conversion was reverted — in "
        "which case the page shows no address at all — or the file moved; update "
        "CONVERTED_TEMPLATES. Without this, the export check below is vacuous."
    )


@pytest.mark.parametrize("rel", CONVERTED_TEMPLATES)
def test_converted_template_email_vars_are_all_exported(rel):
    """A misspelled context variable is not an error — it renders as empty."""
    # Arrange
    exported = site_branding(RequestFactory().get("/"))

    # Act
    unexported = [
        name for name in sorted(set(EMAIL_VAR_RE.findall(_read(rel))))
        if name not in exported
    ]

    # Assert
    assert not unexported, (
        f"{rel} uses {unexported}, which config.context_processors.site_branding "
        "does not export. Django renders an unknown variable as the EMPTY string, "
        "so this ships a blank mailto: rather than raising."
    )


# ---------------------------------------------------------------------------
# Injected sites: the address must actually ARRIVE in the rendered page
# ---------------------------------------------------------------------------
# Source-level checks cannot see the failure that matters. These render the page
# through the real view + URLconf, which is the only thing that proves the
# context processor ran.
@pytest.mark.django_db
@pytest.mark.parametrize("url_name, const_name", CONVERTED_PAGES)
def test_converted_page_returns_http_200(url_name, const_name, client):
    """Anti-vacuity: an error page would not contain the address either."""
    # Arrange
    expected_status = 200

    # Act
    status = client.get(reverse(url_name)).status_code

    # Assert
    assert status == expected_status, (
        f"{url_name} returned HTTP {status}. The address assertions below read "
        "the response body, so they would be vacuous on an error page."
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_name, const_name", CONVERTED_PAGES)
def test_converted_page_renders_the_ssot_address(url_name, const_name, client):
    """The address a public page shows must be the constant, injected live."""
    # Arrange
    expected = getattr(branding, const_name)

    # Act
    content = client.get(reverse(url_name)).content.decode("utf-8")

    # Assert
    assert f"mailto:{expected}" in content, (
        f"{url_name} does not render mailto:{expected}. Either the template lost "
        f"its {{{{ {const_name} }}}} reference, or it is being rendered WITHOUT "
        "context processors — in which case the link is an empty mailto:."
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_name, const_name", CONVERTED_PAGES)
def test_converted_page_renders_no_empty_mailto(url_name, const_name, client):
    """``href="mailto:"`` is the exact shape of an unresolved address."""
    # Arrange
    forbidden = EMPTY_MAILTO

    # Act
    content = client.get(reverse(url_name)).content.decode("utf-8")

    # Assert
    assert forbidden not in content, (
        f"{url_name} renders an empty {forbidden!r}. A context variable that does "
        "not resolve is not an error in Django — it is the empty string, so the "
        "page looks finished and cannot be replied to."
    )


# ---------------------------------------------------------------------------
# Injected site: Python
# ---------------------------------------------------------------------------
@pytest.fixture
def health_sender_override_removed():
    """Really remove the env override, so the code's own default is what ships.

    A real ``os.environ`` mutation with teardown rather than a patched lookup:
    what is under test is the literal the module falls back to when nothing
    overrides it, which is exactly what production sees with the var unset.
    """
    key = "SCITEX_HUB_HEALTH_NOTIFICATION_SENDER"
    previous = os.environ.pop(key, None)
    try:
        yield key
    finally:
        if previous is not None:
            os.environ[key] = previous


def test_health_notification_default_sender_is_the_ssot_noreply(
    health_sender_override_removed,
):
    """The health mailer's default From: is imported, not a private copy."""
    # Arrange
    from apps.infra.public_app.tasks import health

    expected = branding.NOREPLY_EMAIL

    # Act
    _url, _site_url, _recipient, sender = health._get_health_config()

    # Assert
    assert sender == expected, (
        f"the health-notification default sender is {sender!r}, not "
        f"branding.NOREPLY_EMAIL ({expected!r}). This module is plain Python and "
        "can import the SSoT, so it must."
    )


# EOF
