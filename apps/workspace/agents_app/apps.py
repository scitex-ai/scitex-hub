"""AppConfig for the hub-side SAC dashboard mount."""

from django.apps import AppConfig


class AgentsAppConfig(AppConfig):
    name = "apps.workspace.agents_app"
    label = "agents_app"
    verbose_name = "SciTeX Agents Mount"
