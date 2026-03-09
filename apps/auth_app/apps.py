from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_app"
    verbose_name = "Auth"

    def ready(self):
        """Initialize the app when Django starts."""
        pass
