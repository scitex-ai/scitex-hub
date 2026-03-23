from django.urls import path

from .views.ai_setup import (
    ai_setup_hub,
    ai_setup_item_detail,
    ai_setup_mcp_server,
    ai_setup_section,
)

app_name = "ai_setup"

urlpatterns = [
    path("", ai_setup_hub, name="hub"),
    path(
        "api/item/<str:section>/<str:name>/", ai_setup_item_detail, name="item_detail"
    ),
    path("mcp-servers/<str:server>/", ai_setup_mcp_server, name="mcp_server"),
    path("<str:section>/", ai_setup_section, name="section"),
]
