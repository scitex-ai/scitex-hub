"""AppConfig for the hub-side Statistics mount."""

from django.apps import AppConfig


class StatsAppConfig(AppConfig):
    name = "apps.workspace.stats_app"
    label = "stats_app"
    verbose_name = "SciTeX Statistics Mount"


__all__ = ["StatsAppConfig"]
