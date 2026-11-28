#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_mail_brand_icons.py
"""The brand mark that mail clients show is the PRODUCTION favicon.

Operator request (dev@, 2026-11-27): SciTeX mail should carry the official
NAVY SciTeX icon. Two surfaces come from this repo:

* ``branding.EMAIL_HEADER_ICON`` -- the PNG at the top of every Hub HTML mail.
  The header used to point at ``scitex_logos/scitex-logo-cropped.png``, which
  does not exist (production answered 404), so every signup, invitation and
  password-reset mail opened with a broken image.
* ``branding.BIMI_LOGO`` -- the SVG Tiny PS file the ``default._bimi`` DNS
  record will point at. BIMI validators reject anything outside the Tiny PS
  profile, so the profile rules are asserted here rather than discovered when a
  mailbox provider silently ignores the record.

Both are pinned to ``FAVICON_BY_ENV[production]`` so the inbox and the browser
tab cannot drift apart.
"""

from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from config import branding

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC = REPO_ROOT / "static"
SVG_NS = "{http://www.w3.org/2000/svg}"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Modules that build HTML mail bodies by hand.
MAIL_BUILDERS = (
    REPO_ROOT / "apps/infra/project_app/services/email_service.py",
    REPO_ROOT / "apps/infra/auth_app/views/password_reset.py",
)


@pytest.fixture(scope="module")
def favicon_source() -> str:
    return (STATIC / branding.favicon_for_env(branding.ENV_PRODUCTION)).read_text()


@pytest.fixture(scope="module")
def bimi_root() -> ET.Element:
    return ET.parse(STATIC / branding.BIMI_LOGO).getroot()


@pytest.fixture(scope="module")
def header_png() -> bytes:
    return (STATIC / branding.EMAIL_HEADER_ICON).read_bytes()


def test_bimi_logo_declares_the_tiny_ps_profile(bimi_root) -> None:
    # Arrange
    expected = ("1.2", "tiny-ps")
    # Act
    declared = (bimi_root.get("version"), bimi_root.get("baseProfile"))
    # Assert
    assert declared == expected


def test_bimi_logo_root_has_no_x_or_y(bimi_root) -> None:
    # Arrange
    forbidden = ("x", "y")
    # Act
    present = [name for name in forbidden if bimi_root.get(name) is not None]
    # Assert
    assert present == []


def test_bimi_logo_canvas_is_square(bimi_root) -> None:
    # Arrange
    view_box = bimi_root.get("viewBox")
    # Act
    _, _, width, height = (float(v) for v in view_box.split())
    # Assert
    assert width == height


def test_bimi_logo_has_a_title(bimi_root) -> None:
    # Arrange
    tag = f"{SVG_NS}title"
    # Act
    title = bimi_root.find(tag)
    # Assert
    assert getattr(title, "text", None) == "SciTeX"


def test_bimi_logo_uses_no_css_script_or_raster(bimi_root) -> None:
    # Arrange
    allowed = {"svg", "title", "rect", "path"}
    # Act
    tags = {element.tag.removeprefix(SVG_NS) for element in bimi_root.iter()}
    # Assert
    assert tags <= allowed, tags


def test_bimi_logo_background_is_the_favicon_navy(bimi_root, favicon_source) -> None:
    # Arrange
    navy = re.search(r"\.bg-fill \{ fill: (#[0-9a-fA-F]{6}); \}", favicon_source)
    # Act
    fill = bimi_root.find(f"{SVG_NS}rect").get("fill")
    # Assert
    assert fill.lower() == navy.group(1).lower()


def test_bimi_logo_snake_is_the_favicon_snake(bimi_root, favicon_source) -> None:
    # Arrange
    favicon_paths = re.findall(r'<path class="snake-fill" d="([^"]+)"', favicon_source)
    # Act
    bimi_paths = [p.get("d") for p in bimi_root.findall(f"{SVG_NS}path")]
    # Assert
    assert favicon_paths and bimi_paths == favicon_paths


def test_email_header_icon_is_a_png(header_png) -> None:
    # Arrange
    signature_length = len(PNG_SIGNATURE)
    # Act
    signature = header_png[:signature_length]
    # Assert
    assert signature == PNG_SIGNATURE


def test_email_header_icon_is_square_and_sharp(header_png) -> None:
    # Arrange
    ihdr = header_png[16:24]
    # Act
    width, height = struct.unpack(">II", ihdr)
    # Assert
    assert width == height >= 96


@pytest.mark.parametrize("module", MAIL_BUILDERS, ids=lambda p: p.name)
def test_mail_bodies_use_the_brand_icon(module: Path) -> None:
    # Arrange
    source = module.read_text()
    # Act
    uses_icon = "branding.EMAIL_HEADER_ICON" in source
    # Assert
    assert uses_icon


@pytest.mark.parametrize("module", MAIL_BUILDERS, ids=lambda p: p.name)
def test_every_static_file_a_mail_names_exists(module: Path) -> None:
    """A mail cannot be re-sent once a recipient sees a broken image."""
    # Arrange
    named = re.findall(r"/static/(shared/[^\"'\s{}]+)", module.read_text())
    # Act
    missing = [path for path in named if not (STATIC / path).is_file()]
    # Assert
    assert not missing, missing
