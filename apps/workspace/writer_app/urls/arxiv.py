from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path(
        "submit/",
        TemplateView.as_view(template_name="writer_app/arxiv/submission.html"),
        name="submit",
    ),
]
