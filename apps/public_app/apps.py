from django.apps import AppConfig


class PublicAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_app"
    verbose_name = "Tools"
