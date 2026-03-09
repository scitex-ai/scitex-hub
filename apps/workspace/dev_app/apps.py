from django.apps import AppConfig


class DevAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.dev_app"
    verbose_name = "Development Tools"
