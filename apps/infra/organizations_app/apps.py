from django.apps import AppConfig


class OrganizationsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.organizations_app"
    verbose_name = "Organizations"

    def ready(self):
        import apps.infra.organizations_app.signals  # noqa: F401
