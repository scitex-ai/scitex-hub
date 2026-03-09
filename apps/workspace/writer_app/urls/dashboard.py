from django.urls import path
from ..views.index.main import index, initialize_workspace

urlpatterns = [
    # Main writer page - simple editor with PDF viewer
    path("", index, name="index"),
    # Initialize workspace API
    path("initialize/", initialize_workspace, name="initialize_workspace"),
]
