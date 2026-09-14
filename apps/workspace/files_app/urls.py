from django.urls import path

from . import views

app_name = "files_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/list/", views.api_list, name="api_list"),
    path("api/upload/", views.api_upload, name="api_upload"),
    path("api/mkdir/", views.api_mkdir, name="api_mkdir"),
    path("api/rename/", views.api_rename, name="api_rename"),
    path("api/move/", views.api_move, name="api_move"),
    path("api/delete/", views.api_delete, name="api_delete"),
    path("download/", views.download, name="download"),
    path("raw/", views.raw, name="raw"),
]
