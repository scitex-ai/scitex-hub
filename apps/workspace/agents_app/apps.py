"""AppConfig for the hub-side Agents dashboard mount."""

from django.apps import AppConfig


class AgentsAppConfig(AppConfig):
    name = "apps.workspace.agents_app"
    label = "agents_app"
    verbose_name = "SciTeX Agents Mount"


__all__ = ["AgentsAppConfig"]
