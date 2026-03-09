from django.urls import path

from .views import file_content, file_save

app_name = "workspace_api"

urlpatterns = [
    path(
        "file-content/<path:file_path>",
        file_content.api_get_file_content,
        name="file_content",
    ),
    path(
        "save-file/",
        file_save.api_save_file,
        name="save_file",
    ),
]

# EOF
