"""Serve the real hub URLconf as it is composed with developer tools enabled.

``config.urls`` decides at import time whether ``/dev/`` is mounted, and the
test settings leave ``DEV_TOOLS_ENABLED`` off. To exercise an enabled
deployment, the same mount helper (``config.urls._dev_tools_patterns``) is
evaluated with the setting on and placed in front of the hub's own routes,
in a module that ``ROOT_URLCONF`` then points at.
"""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager

ENABLED_URLCONF = "tests_dev_tools_enabled_urlconf"


@contextmanager
def dev_tools_enabled_urlconf(settings):
    """Enable developer tools and route requests through a remounted URLconf.

    ``settings`` is pytest-django's settings fixture, which restores both
    values (and clears the URL caches) afterwards.
    """
    import config.urls as root

    settings.DEV_TOOLS_ENABLED = True
    module = types.ModuleType(ENABLED_URLCONF)
    module.urlpatterns = root._dev_tools_patterns() + list(root.urlpatterns)
    sys.modules[ENABLED_URLCONF] = module
    settings.ROOT_URLCONF = ENABLED_URLCONF
    try:
        yield
    finally:
        sys.modules.pop(ENABLED_URLCONF, None)
