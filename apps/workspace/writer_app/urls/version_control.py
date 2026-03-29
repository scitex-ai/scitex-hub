from django.urls import path
from ..views.version_control.dashboard import version_control_index

urlpatterns = [
    path(
        "",
        version_control_index,
        name="index",
    ),
]
