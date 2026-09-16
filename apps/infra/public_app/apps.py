from django.apps import AppConfig


class PublicAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.public_app"
    verbose_name = "Public"

    def ready(self):
        # Import for its @register side effect. Without this the check is
        # defined and never runs -- the shape that leaves a "check" green
        # forever because nothing consumes it.
        from apps.infra.public_app import checks  # noqa: F401
