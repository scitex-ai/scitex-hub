"""Django app configuration for Live Paper."""

from django.apps import AppConfig


class LivePaperAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scitex_live_paper_hub_app"
    verbose_name = "Live Paper"
