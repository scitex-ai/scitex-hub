"""Apps views package."""

from .api import (
    api_fork,
    api_install,
    api_list_public,
    api_reorder,
    api_review,
    api_review_submission,
    api_star,
    api_submit_for_review,
    api_toggle,
    api_uninstall,
    api_unstar,
    api_update_config,
)
from .pages import browse, build_apps_context, detail, my_modules, review_queue

__all__ = [
    "browse",
    "build_apps_context",
    "detail",
    "my_modules",
    "api_install",
    "api_uninstall",
    "api_toggle",
    "api_star",
    "api_unstar",
    "api_review",
    "api_reorder",
    "api_submit_for_review",
    "api_review_submission",
    "api_update_config",
    "api_fork",
    "api_list_public",
    "review_queue",
]
