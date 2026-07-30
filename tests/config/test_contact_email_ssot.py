#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Three files must repeat the contact address as a literal; pin them to the SSoT.

Most sites read ``CONTACT_EMAIL`` through the ``site_branding`` context
processor. Three cannot, for reasons that are not stylistic:

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

import re
from pathlib import Path

import pytest
from django.conf import settings

from config import branding

# Files that must repeat the address because they cannot read Django context.
LITERAL_SITES = (
    "templates/500.html",
    "deployment/docker/common/nginx/error-pages/502.html",
    "deployment/docker/Dockerfile.user-workspace",
)

ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@scitex\.ai")


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


def test_contact_email_is_built_from_the_shared_domain():
    """A domain move must be one edit, so the address may not hardcode it."""
    # Arrange
    expected_suffix = "@" + branding.CONTACT_DOMAIN

    # Act
    actual = branding.CONTACT_EMAIL

    # Assert
    assert actual.endswith(expected_suffix), (
        f"CONTACT_EMAIL ({actual}) does not end with {expected_suffix}; it should "
        "be composed from CONTACT_DOMAIN so the domain stays single-sourced."
    )


# EOF
