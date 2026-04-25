"""Django AppConfig for A2A protocol surface."""

from django.apps import AppConfig


class A2AAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.a2a_app"
    label = "a2a_app"
    verbose_name = "A2A protocol"
