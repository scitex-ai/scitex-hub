"""Django AppConfig — cloud-side thin wrapper.

The hub workspace mounts each ``apps/workspace/*_app`` package as a
Django app via its ``AppConfig``. For the agentic journal we delegate
the embedded surface to the upstream package; this config exists only
so the workspace registration is uniform.
"""

from __future__ import annotations

from django.apps import AppConfig


class AgenticJournalAppConfig(AppConfig):
    """Cloud-side wrapper for ``scitex_agentic_journal._django``."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.agentic_journal_app"
    label = "agentic_journal_app"
    verbose_name = "Agentic Journal"

    def ready(self) -> None:
        """Eagerly validate the upstream manifest at process start.

        If `scitex_agentic_journal` isn't installed (e.g. a hub deploy
        that doesn't host journal traffic) we fail **loud** at boot,
        not silently when an operator opens the page. No silent
        fallback to "the app exists but the dashboard is blank".
        """
        try:
            from scitex_agentic_journal._django import load_manifest
        except ImportError as exc:
            raise RuntimeError(
                "agentic_journal_app requires `scitex-agentic-journal` to be "
                "installed. Run `pip install scitex-agentic-journal` or remove "
                "this app from INSTALLED_APPS for hub deployments that don't "
                "host the journal surface."
            ) from exc
        load_manifest()
