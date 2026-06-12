"""Django AppConfig — cloud-side thin wrapper.

The hub workspace mounts each ``apps/workspace/*_app`` package as a
Django app via its ``AppConfig``. For the agentic journal we delegate
the embedded surface to the upstream package; this config exists only
so the workspace registration is uniform.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig

_logger = logging.getLogger(__name__)


class AgenticJournalAppConfig(AppConfig):
    """Cloud-side wrapper for ``scitex_agentic_journal._django``."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.agentic_journal_app"
    label = "agentic_journal_app"
    verbose_name = "Agentic Journal"

    def ready(self) -> None:
        """Probe the upstream manifest and warn (not raise) if missing.

        Earlier this method raised on a missing upstream, but Django's
        ``populate(INSTALLED_APPS)`` runs even in CI where the upstream
        package may not be installed (it isn't yet a hard dep of
        scitex-hub since `scitex-agentic-journal` is pre-alpha and not
        on PyPI). Raising there crashes every Django startup including
        the unrelated pytest matrix.

        The "fail loud" doctrine still holds — the **request path**
        raises clearly (see ``urls.py`` lazy include + ``manifest`` view)
        if a user hits the dashboard with no upstream installed. Boot
        is permissive; runtime is strict.
        """
        try:
            from scitex_agentic_journal._django import load_manifest
        except ImportError:
            _logger.warning(
                "agentic_journal_app: `scitex-agentic-journal` is not "
                "installed. Dashboard URLs will return 500 with a typed "
                "error until you `pip install scitex-agentic-journal` or "
                "remove this app from INSTALLED_APPS."
            )
            return
        load_manifest()
