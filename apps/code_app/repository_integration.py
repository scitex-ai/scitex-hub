"""
Repository integration for Code execution results.
Re-exports from apps.code_app.integrations.repository_integration for backward compatibility.
"""

from .integrations.repository_integration import (
    CodeRepositoryIntegrator,
    auto_sync_code_completion,
    sync_project_data_to_repository,
)

__all__ = [
    "CodeRepositoryIntegrator",
    "auto_sync_code_completion",
    "sync_project_data_to_repository",
]
