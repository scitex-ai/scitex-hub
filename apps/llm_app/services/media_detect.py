"""Thin wrapper — delegates to scitex.media.render.

Django consumers import ``extract_media_refs`` and ``MEDIA_EXTENSIONS``
from here. The actual logic lives in ``scitex.media.render``.
"""

from scitex.media.render import MEDIA_EXTENSIONS  # noqa: F401
from scitex.media.render import detect as extract_media_refs  # noqa: F401

# EOF
