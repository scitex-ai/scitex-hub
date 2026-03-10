"""
Writer App Views - Feature-based Organization

Views are organized by feature domain (index, editor, compilation, etc.)
Legacy views remain in legacy/ folder for backward compatibility.
"""

# Import from index for backward compatibility
from .index.main import index_view

# Feature-based views (new structure)
try:
    from .index.main import *
except ImportError:
    pass

try:
    from .editor.editor import *
except ImportError:
    pass

try:
    from .compilation.compilation import *
except ImportError:
    pass

try:
    from .collaboration.session import *
except ImportError:
    pass

try:
    from .version_control.index import *
except ImportError:
    pass

try:
    from .arxiv.submission import *
except ImportError:
    pass

__all__ = [
    # Main
    "index",
    "initialize_workspace",
    "user_default_workspace",
    "project_writer",
    # Presence
    "presence_update_view",
    "presence_list_view",
    # API stubs
    "save_section",
    "load_latex_section",
    "save_latex_section",
    "list_tex_files",
    "compile_modular_manuscript",
    "cloud_compile_sections",
    "quick_compile",
    "compilation_status",
    "download_compiled_pdf",
    "download_paper_zip",
    "get_manuscript_stats",
    "toggle_editing_mode",
    # Editors
    "collaborative_editor",
    "features",
    "pricing",
    "modular_editor",
    "simple_editor",
    "latex_editor_view",
    "writer_index_view",
    "manuscript_list",
    "mock_save",
    # Collaboration
    "collaborative_sessions",
    "join_collaboration",
    "leave_collaboration",
    "lock_section",
    "unlock_section",
    # Version control
    "version_history",
    "create_version",
    "view_diff",
    "rollback_version",
    "branch_list",
    "create_branch",
    "create_merge_request",
    "version_control_index",
    # arXiv
    "ArxivIndexView",
    "SubmissionListView",
    "arxiv_account_setup",
    "manuscript_submission_form",
    "submission_detail",
    "validate_submission",
    "prepare_submission_files",
    "submit_to_arxiv",
    "check_submission_status",
    "withdraw_submission",
    "create_replacement",
    "submission_history_api",
    "categories_api",
    "suggest_categories_api",
    "arxiv_status_check",
    "initialize_categories",
]
