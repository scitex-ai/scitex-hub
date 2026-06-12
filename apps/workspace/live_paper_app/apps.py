"""Django AppConfig — cloud-side thin wrapper for scitex-live-paper.

Boot is permissive; runtime is strict. If ``scitex-live-paper`` is not
installed (not yet a hard dep — pre-alpha, not on PyPI), Django still
boots and the wrapper logs a warning. The dashboard URL `apps/
live-paper/` then surfaces a typed 500 on first request via the lazy
``include("scitex_live_paper._django.urls")`` in ``urls.py``.

This mirrors the agentic_journal_app wrapper's docstring on the same
contract; both apps share the wrapper pattern.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig

_logger = logging.getLogger(__name__)


class LivePaperAppConfig(AppConfig):
    """Cloud-side wrapper for ``scitex_live_paper._django``."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.live_paper_app"
    label = "live_paper_app"
    verbose_name = "Live Paper"

    def ready(self) -> None:
        """Probe the upstream package and warn (not raise) if missing.

        The fail-loud doctrine still holds — the **request path** dies
        loudly when a user hits ``/apps/live-paper/`` with no upstream
        installed: ``urls.py`` calls ``django.urls.include(
        "scitex_live_paper._django.urls")``, which Django resolves
        lazily on the first URL match. With the upstream absent that
        resolve raises ``ImportError`` and Django renders a 500.
        """
        try:
            import scitex_live_paper._django  # noqa: F401
        except ImportError:
            _logger.warning(
                "live_paper_app: `scitex-live-paper` is not installed. "
                "Dashboard URLs (/apps/live-paper/) will return 500 with "
                "a typed error until you `pip install scitex-live-paper` "
                "or remove this app from INSTALLED_APPS."
            )
            return
