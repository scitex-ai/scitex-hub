"""Broker-side data-dir paths used by terminal_broker handlers.

Defined here, not re-imported from ``apps/workspace/console_app/views/
terminal/config``, because the views.terminal.config module gets a
sys.modules stub installed by
``tests/custom/apps/console_app/views/terminal/test_execution.py`` (sibling
tests leave that stub in place across the whole session). A function-
local import of ``USER_DATA_ROOT`` from views/terminal/config in
``_handlers_shared.handle_spawn_shared`` therefore hit ImportError under
test once PR #275 introduced it (caught by lead's pytest-matrix verify
on 2026-06-13 → develop hotfix PR #276).

Production behaviour mirrors views/terminal/config.py exactly: if
``settings.USER_DATA_ROOT`` is set (via env var
``SCITEX_HUB_USER_DATA_ROOT``), it wins; otherwise the canonical
Docker-internal mount path ``/app/data/users`` is used. No silent
fallback — the documented default is the same value the production
container already pins.
"""

from pathlib import Path

from django.conf import settings

#: Docker-internal data-dir mount baked into the production image.
_BROKER_USER_DATA_ROOT_DEFAULT = Path("/app/data/users")


def broker_user_data_root() -> Path:
    """Return the broker Docker-internal root of the user-data mount."""
    return Path(
        getattr(settings, "USER_DATA_ROOT", None) or _BROKER_USER_DATA_ROOT_DEFAULT
    )
