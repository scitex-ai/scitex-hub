"""Apps views package."""

from .api import (
    api_fork,
    api_install,
    api_list_public,
    api_reorder,
    api_review,
    api_star,
    api_toggle,
    api_uninstall,
    api_unstar,
    api_update_config,
)
from .api_dev import api_dev_install, api_dev_uninstall
from .api_registry import api_registry_webhook, api_submit_jwt
from .api_submission import api_review_submission, api_submit_for_review
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
    "api_submit_jwt",
    "api_registry_webhook",
    "api_dev_install",
    "api_dev_uninstall",
    "review_queue",
]
