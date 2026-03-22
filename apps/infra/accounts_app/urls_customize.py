from django.urls import path

from .views.customize import customize_hub

app_name = "customize"

urlpatterns = [
    path("", customize_hub, name="hub"),
]
