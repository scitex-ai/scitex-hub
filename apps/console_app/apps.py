from django.apps import AppConfig


class ConsoleAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.console_app"
    verbose_name = "Console"
