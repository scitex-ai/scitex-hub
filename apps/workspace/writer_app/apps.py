from django.apps import AppConfig


class WriterAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.writer_app"
    verbose_name = "Writer"
