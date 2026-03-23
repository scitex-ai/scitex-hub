from django.urls import path

from .views.customize import customize_hub, customize_mcp_server, customize_section

app_name = "customize"

urlpatterns = [
    path("", customize_hub, name="hub"),
    path("mcp-servers/<str:server>/", customize_mcp_server, name="mcp_server"),
    path("<str:section>/", customize_section, name="section"),
]
