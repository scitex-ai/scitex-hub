"""
Repository Feature URLs

Handles all repository browsing, file viewing, and commit history URLs.
GitHub-style patterns:
- /<username>/<slug>/ - Repository root
- /<username>/<slug>/blob/<path> - File view
- /<username>/<slug>/commits/<branch>/<path> - File history
- /<username>/<slug>/commit/<hash>/ - Commit detail
- /<username>/<slug>/<directory-path>/ - Directory browsing
"""

from django.urls import path

from ..views.api import (
    api_concatenate_directory,
    api_file_tree,
)
from ..views.directory_views import (
    commit_detail,
    file_history_view,
    project_directory_dynamic,
    project_file_view,
)
from ..views.projects import (
    project_detail,
)
from ..views.repository.api import (
    api_app_scaffold,
    api_app_status,
    api_app_submit,
    api_app_validate,
    api_create_symlink,
    api_extract_bundle,
    api_file_copy,
    api_file_create,
    api_file_delete,
    api_file_move,
    api_file_rename,
    api_file_upload,
    api_file_upload_url,
    api_git_commit,
    api_git_diff,
    api_git_discard,
    api_git_history,
    api_git_pull,
    api_git_push,
    api_git_stage,
    api_git_stage_all,
    api_git_status,
    api_git_unstage,
    api_git_unstage_all,
    api_initialize_scitex_structure,
)

# Note: slug and username are passed via kwargs from parent URL pattern
# No app_name here - namespace is provided by parent (project_app)
urlpatterns = [
    # Project root - Repository overview
    # /<username>/<slug>/
    path("", project_detail, name="detail"),
    # API endpoint for file tree (sidebar navigation)
    path("api/file-tree/", api_file_tree, name="api_file_tree"),
    # API endpoint for git status (git gutter indicators)
    path("api/git/status/", api_git_status, name="api_git_status"),
    # Git operations API
    path("api/git/stage/", api_git_stage, name="api_git_stage"),
    path("api/git/unstage/", api_git_unstage, name="api_git_unstage"),
    path("api/git/discard/", api_git_discard, name="api_git_discard"),
    path("api/git/commit/", api_git_commit, name="api_git_commit"),
    path("api/git/history/", api_git_history, name="api_git_history"),
    path("api/git/diff/", api_git_diff, name="api_git_diff"),
    path("api/git/stage-all/", api_git_stage_all, name="api_git_stage_all"),
    path("api/git/unstage-all/", api_git_unstage_all, name="api_git_unstage_all"),
    path("api/git/push/", api_git_push, name="api_git_push"),
    path("api/git/pull/", api_git_pull, name="api_git_pull"),
    # API endpoint to initialize SciTeX structure (works for both local and remote projects)
    path(
        "api/initialize-scitex/",
        api_initialize_scitex_structure,
        name="api_initialize_scitex",
    ),
    # API endpoint to concatenate all files in a directory
    path("api/concatenate/", api_concatenate_directory, name="api_concatenate_root"),
    path(
        "api/concatenate/<path:directory_path>",
        api_concatenate_directory,
        name="api_concatenate",
    ),
    # File CRUD operations API
    path("api/files/create/", api_file_create, name="api_file_create"),
    path("api/files/delete/", api_file_delete, name="api_file_delete"),
    path("api/files/rename/", api_file_rename, name="api_file_rename"),
    path("api/files/copy/", api_file_copy, name="api_file_copy"),
    path("api/files/move/", api_file_move, name="api_file_move"),
    path("api/files/upload/", api_file_upload, name="api_file_upload"),
    path("api/files/upload-url/", api_file_upload_url, name="api_file_upload_url"),
    path("api/files/symlink/", api_create_symlink, name="api_create_symlink"),
    path("api/files/extract-bundle/", api_extract_bundle, name="api_extract_bundle"),
    # App submission API
    path("api/app/validate/", api_app_validate, name="api_app_validate"),
    path("api/app/submit/", api_app_submit, name="api_app_submit"),
    path("api/app/status/", api_app_status, name="api_app_status"),
    path("api/app/scaffold/", api_app_scaffold, name="api_app_scaffold"),
    # File viewer - GitHub-style /blob/ for viewing files
    # /<username>/<slug>/blob/<file-path> - default view
    # /<username>/<slug>/blob/<file-path>?mode=edit - edit mode
    # /<username>/<slug>/blob/<file-path>?mode=raw - raw mode
    path("blob/<path:file_path>", project_file_view, name="file_view"),
    # File history - GitHub-style /commits/<branch>/<file-path>
    # /<username>/<slug>/commits/<branch>/<file-path>
    path(
        "commits/<str:branch>/<path:file_path>", file_history_view, name="file_history"
    ),
    # Commit detail - GitHub-style /commit/<commit-hash>/
    # /<username>/<slug>/commit/<commit-hash>/
    path("commit/<str:commit_hash>/", commit_detail, name="commit_detail"),
    # Dynamic directory browsing - catches ANY directory path (MUST BE LAST!)
    # /<username>/<slug>/<any-directory>/
    # /<username>/<slug>/<any-directory>/<any-subdirectory>/...
    path("<path:directory_path>/", project_directory_dynamic, name="directory_browse"),
]
