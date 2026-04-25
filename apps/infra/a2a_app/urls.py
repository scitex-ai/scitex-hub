"""URL patterns for the A2A protocol app.

Mounted at root by config/urls.py so that paths land where A2A expects:
  /.well-known/agent.json
  /v1/agents/
  /v1/agents/<name>/.well-known/agent.json
  /v1/agents/<name>
"""

from apps.infra.a2a_app import views
from django.urls import path

app_name = "a2a"

urlpatterns = [
    path(".well-known/agent.json", views.fleet_well_known, name="fleet-card"),
    path("v1/agents/", views.agents_index, name="agents-index"),
    path(
        "v1/agents/<str:name>/.well-known/agent.json",
        views.agent_well_known,
        name="agent-card",
    ),
    path("v1/agents/<str:name>", views.agent_jsonrpc, name="agent-jsonrpc"),
]
