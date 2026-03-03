from django.apps import AppConfig


class PlatformAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform_app"
    verbose_name = "Platform Services"
