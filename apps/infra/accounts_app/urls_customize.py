from django.urls import path

from .views.customize import customize_hub, customize_section

app_name = "customize"

urlpatterns = [
    path("", customize_hub, name="hub"),
    path("<str:section>/", customize_section, name="section"),
]
