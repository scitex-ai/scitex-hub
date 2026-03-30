from django.apps import AppConfig


class CommsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.comms_app"
    verbose_name = "Communications"

    def ready(self):
        import apps.workspace.comms_app.signals  # noqa: F401
