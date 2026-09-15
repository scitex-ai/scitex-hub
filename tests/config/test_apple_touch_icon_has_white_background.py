# -*- coding: utf-8 -*-
# File: tests/config/test_apple_touch_icon_has_white_background.py
"""The iOS home-screen icon padding must be opaque white.

iOS renders transparent (or dark) padding as black; the operator wants the
navy circle logo centred on white.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ICON = (
    Path(__file__).resolve().parents[2]
    / "static/shared/images/favicons/apple-touch-icon-padded-180.png"
)


def test_apple_touch_icon_corner_pixel_is_opaque_white():
    # Arrange
    image = Image.open(ICON).convert("RGBA")

    # Act
    corner = image.getpixel((0, 0))

    # Assert
    assert corner == (255, 255, 255, 255)


# EOF
