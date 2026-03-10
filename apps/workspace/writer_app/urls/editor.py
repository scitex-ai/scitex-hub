from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="writer_app/editor/editor.html"),
        name="editor",
    ),
]
