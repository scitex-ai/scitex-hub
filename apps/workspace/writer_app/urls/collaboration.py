from django.urls import path
from django.views.generic import TemplateView

from ..views.collaboration.comments import (
    create_comment,
    delete_comment,
    list_comments,
    reanchor_comments,
    resolve_comment,
    update_comment,
)
from ..views.collaboration.presence import active_api, heartbeat_api

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="writer_app/collaboration/session.html"),
        name="session",
    ),
    # Presence heartbeat (leaf editor collab pane polls these)
    path(
        "presence/heartbeat/",
        heartbeat_api,
        name="presence-heartbeat",
    ),
    path(
        "presence/active/",
        active_api,
        name="presence-active",
    ),
    # Comment/annotation API
    path(
        "comments/<int:manuscript_id>/",
        list_comments,
        name="comment-list",
    ),
    path(
        "comments/<int:manuscript_id>/create/",
        create_comment,
        name="comment-create",
    ),
    path(
        "comments/<int:manuscript_id>/<int:comment_id>/update/",
        update_comment,
        name="comment-update",
    ),
    path(
        "comments/<int:manuscript_id>/<int:comment_id>/resolve/",
        resolve_comment,
        name="comment-resolve",
    ),
    path(
        "comments/<int:manuscript_id>/<int:comment_id>/delete/",
        delete_comment,
        name="comment-delete",
    ),
    path(
        "comments/<int:manuscript_id>/reanchor/",
        reanchor_comments,
        name="comment-reanchor",
    ),
]
