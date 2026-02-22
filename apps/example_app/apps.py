from django.apps import AppConfig


class ExampleAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.example_app"
    verbose_name = "Example Module"
