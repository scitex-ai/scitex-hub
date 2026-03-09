from django.apps import AppConfig


class SocialAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.social_app"
    verbose_name = "Social Features"

    def ready(self):
        """Import signals when app is ready"""
        # Import signals if needed in the future
        pass
