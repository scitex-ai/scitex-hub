"""
Pull Requests Feature URLs

Handles pull request list at /pulls/.
Individual PR URLs are handled in main __init__.py at /pull/<number>/ (singular).

GitHub-style patterns:
- /<username>/<slug>/pulls/ - List all PRs (this file)
- /<username>/<slug>/pull/new/ - Create new PR (in __init__.py)
- /<username>/<slug>/pull/<number>/ - PR detail (in __init__.py)
- /<username>/<slug>/compare/<compare>/ - Compare branches (in __init__.py)
"""

from django.urls import path
from ..views.pr import (
    pr_list,
)

# No app_name here - namespace is provided by parent (user_projects)

urlpatterns = [
    # Pull Request list only
    # Individual PRs are at /pull/ (singular) not /pulls/
    path("", pr_list, name="list"),
]
