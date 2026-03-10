from django.apps import AppConfig


class ProjectAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.project_app"
    verbose_name = "Project Management"

    def ready(self):
        """Initialize the app when Django starts."""
        # Import signals to register them
        from . import signals
