# -*- coding: utf-8 -*-
# File: tests/config/test_apple_touch_icon_is_padded.py
"""The iOS home-screen icon must be the PADDED variant.

The operator installed the site as an iPhone home-screen app and the old icon
(brand circle drawn edge to edge) touched the rounded-square mask. The fix
serves a variant with the circle at ~70% of the tile. This pins the rendered
base head to that file, and proves the file is actually present in static so
the link cannot silently 404 into iOS's screenshot fallback.
"""

from __future__ import annotations

import re

from django.conf import settings

from ._branding_helpers import render

PADDED_ICON = "shared/images/favicons/apple-touch-icon-padded-180.png"


def test_base_head_apple_touch_icon_points_at_existing_padded_file():
    # Arrange
    source = '{% include "global_base_partials/global_head_meta.html" %}'

    # Act
    html = render(source, path="/")
    href = re.search(r'rel="apple-touch-icon"[^>]*href="([^"?]+)', html).group(1)
    relative = href.removeprefix(settings.STATIC_URL)
    on_disk = settings.BASE_DIR / "static" / relative

    # Assert
    assert (relative, on_disk.is_file()) == (PADDED_ICON, True)


# EOF
