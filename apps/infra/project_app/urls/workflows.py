"""
Workflows Feature URLs

Handles all CI/CD workflow and GitHub Actions related URLs.
GitHub-style patterns:
- /<username>/<slug>/actions/ - Actions/workflows list
- /<username>/<slug>/actions/new/ - Create new workflow
- /<username>/<slug>/actions/workflows/<id>/ - Workflow detail
- /<username>/<slug>/actions/runs/<id>/ - Workflow run detail

Note: Currently commented out pending Workflow model implementation.
"""

# No app_name here - namespace is provided by parent (project_app)

# TODO: Uncomment when Workflow models are implemented
# from ..views.actions_views import (
#     actions_list,
#     workflow_create,
#     workflow_detail,
#     workflow_edit,
#     workflow_delete,
#     workflow_trigger,
#     workflow_enable_disable,
#     workflow_run_detail,
# )

urlpatterns = [
    # Placeholder - uncomment when models are ready
    # path('', actions_list, name='list'),
    # path('new/', workflow_create, name='create'),
    # path('workflows/<int:workflow_id>/', workflow_detail, name='detail'),
    # path('workflows/<int:workflow_id>/edit/', workflow_edit, name='edit'),
    # path('workflows/<int:workflow_id>/delete/', workflow_delete, name='delete'),
    # path('workflows/<int:workflow_id>/trigger/', workflow_trigger, name='trigger'),
    # path('workflows/<int:workflow_id>/toggle/', workflow_enable_disable, name='enable_disable'),
    # path('runs/<int:run_id>/', workflow_run_detail, name='run_detail'),
]
