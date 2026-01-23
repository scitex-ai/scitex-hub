#!/usr/bin/env python3
"""
Views package for SciTeX-Code application.
Exports all views for backward compatibility.

Organized into logical modules:
- navigation_views: Basic navigation and landing pages
- job_views: Job execution and monitoring
- notebook_views: Jupyter notebook management
- analysis_views: Data analysis interface
- environment_views: Execution environment management
- workflow_views: Research workflow management
- visualization_views: Data visualization pipeline
- workspace_views: Default workspace views
- project_views: Project-specific views
- api_views: REST API endpoints (separate package)
- service_api_views: Service API endpoints
"""

# Navigation and landing pages
from .navigation_views import (
    index,
    features,
    pricing,
    editor,
)

# Job management
from .job_views import (
    jobs,
    job_detail,
    execute_code,
    job_status,
    get_job_progress,
)

# Notebook management
from .notebook_views import (
    notebooks,
    notebook_detail,
    create_notebook,
    execute_notebook,
)

# Analysis interface
from .analysis_views import (
    analysis,
    templates,
    run_analysis,
)

# Environment management
from .environment_views import (
    environments,
    create_environment,
    setup_environment,
    environment_detail,
    execute_in_environment,
)

# Workflow management
from .workflow_views import (
    workflows,
    create_workflow,
    execute_workflow,
    workflow_detail,
)

# Visualization pipeline
from .visualization_views import (
    visualizations,
    generate_visualization,
    process_data_visualization,
    create_research_report,
)

# Workspace views
from .workspace_views import (
    guest_session_view,
    user_default_workspace,
)

# Project views
from .project_views import (
    project_code,
)

__all__ = [
    # Navigation views
    "index",
    "features",
    "pricing",
    "editor",
    # Job views
    "jobs",
    "job_detail",
    "execute_code",
    "job_status",
    "get_job_progress",
    # Notebook views
    "notebooks",
    "notebook_detail",
    "create_notebook",
    "execute_notebook",
    # Analysis views
    "analysis",
    "templates",
    "run_analysis",
    # Environment views
    "environments",
    "create_environment",
    "setup_environment",
    "environment_detail",
    "execute_in_environment",
    # Workflow views
    "workflows",
    "create_workflow",
    "execute_workflow",
    "workflow_detail",
    # Visualization views
    "visualizations",
    "generate_visualization",
    "process_data_visualization",
    "create_research_report",
    # Workspace views
    "guest_session_view",
    "user_default_workspace",
    # Project views
    "project_code",
]
