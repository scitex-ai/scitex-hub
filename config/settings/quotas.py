"""
Resource Quota Settings for SciTeX Cloud.

Loads quota configurations from environment variables.
These can be overridden per-user in the database.
"""

import os


def get_int(key: str, default: int) -> int:
    """Get integer from environment variable."""
    return int(os.environ.get(key, default))


def get_float(key: str, default: float) -> float:
    """Get float from environment variable."""
    return float(os.environ.get(key, default))


def get_str(key: str, default: str) -> str:
    """Get string from environment variable."""
    return os.environ.get(key, default)


def get_list(key: str, default: str) -> list:
    """Get comma-separated list from environment variable."""
    return os.environ.get(key, default).split(',')


# =============================================================================
# SLURM Job Quotas (Heavy Compute)
# =============================================================================

SLURM_QUOTAS = {
    # Job limits
    'max_concurrent_jobs': get_int('SCITEX_QUOTA_SLURM_MAX_CONCURRENT_JOBS', 4),
    'max_queued_jobs': get_int('SCITEX_QUOTA_SLURM_MAX_QUEUED_JOBS', 10),

    # Resource limits
    'max_cpu_hours_daily': get_int('SCITEX_QUOTA_SLURM_MAX_CPU_HOURS_DAILY', 24),
    'max_cpu_hours_monthly': get_int('SCITEX_QUOTA_SLURM_MAX_CPU_HOURS_MONTHLY', 500),
    'max_memory_gb_per_job': get_int('SCITEX_QUOTA_SLURM_MAX_MEMORY_GB_PER_JOB', 8),
    'max_runtime_hours': get_int('SCITEX_QUOTA_SLURM_MAX_RUNTIME_HOURS', 24),

    # Partitions
    'default_partition': get_str('SCITEX_QUOTA_SLURM_DEFAULT_PARTITION', 'normal'),
    'allowed_partitions': get_list('SCITEX_QUOTA_SLURM_ALLOWED_PARTITIONS', 'normal,express,long'),

    # Interactive terminal
    'interactive_partition': get_str('SCITEX_QUOTA_SLURM_INTERACTIVE_PARTITION', 'express'),
    'interactive_time_limit': get_str('SCITEX_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT', '04:00:00'),
    'interactive_cpus': get_int('SCITEX_QUOTA_SLURM_INTERACTIVE_CPUS', 2),
    'interactive_memory_gb': get_int('SCITEX_QUOTA_SLURM_INTERACTIVE_MEMORY_GB', 4),
}


# =============================================================================
# Celery Rate Limits (Async I/O Tasks)
# =============================================================================

CELERY_QUOTAS = {
    # Rate limits (per minute/hour)
    'ai_calls_per_minute': get_int('SCITEX_QUOTA_CELERY_AI_CALLS_PER_MINUTE', 10),
    'search_per_minute': get_int('SCITEX_QUOTA_CELERY_SEARCH_PER_MINUTE', 30),
    'compute_per_minute': get_int('SCITEX_QUOTA_CELERY_COMPUTE_PER_MINUTE', 20),
    'pdf_per_hour': get_int('SCITEX_QUOTA_CELERY_PDF_PER_HOUR', 100),

    # Task limits
    'max_task_runtime': get_int('SCITEX_QUOTA_CELERY_MAX_TASK_RUNTIME', 600),
}


# =============================================================================
# Storage Quotas
# =============================================================================

STORAGE_QUOTAS = {
    'total_gb': get_int('SCITEX_QUOTA_STORAGE_TOTAL_GB', 50),
    'project_max_gb': get_int('SCITEX_QUOTA_STORAGE_PROJECT_MAX_GB', 10),
    'file_upload_mb': get_int('SCITEX_QUOTA_STORAGE_FILE_UPLOAD_MB', 100),
    'temp_gb': get_int('SCITEX_QUOTA_STORAGE_TEMP_GB', 5),
}


# =============================================================================
# Project & Collaboration Quotas
# =============================================================================

PROJECT_QUOTAS = {
    'max_projects': get_int('SCITEX_QUOTA_MAX_PROJECTS', 50),
    'max_collaborators_per_project': get_int('SCITEX_QUOTA_MAX_COLLABORATORS_PER_PROJECT', 20),
    'max_api_keys': get_int('SCITEX_QUOTA_MAX_API_KEYS', 10),
}


# =============================================================================
# HTTP & WebSocket Quotas
# =============================================================================

HTTP_QUOTAS = {
    'requests_per_minute': get_int('SCITEX_QUOTA_HTTP_REQUESTS_PER_MINUTE', 120),
    'websocket_connections': get_int('SCITEX_QUOTA_WEBSOCKET_CONNECTIONS', 10),
}


# =============================================================================
# Combined Default Quotas (for new users)
# =============================================================================

DEFAULT_USER_QUOTAS = {
    'slurm': SLURM_QUOTAS,
    'celery': CELERY_QUOTAS,
    'storage': STORAGE_QUOTAS,
    'project': PROJECT_QUOTAS,
    'http': HTTP_QUOTAS,
}


def get_user_quotas(user) -> dict:
    """
    Get quotas for a specific user.

    First checks for per-user overrides in database,
    then falls back to default quotas from environment.

    Args:
        user: Django User instance

    Returns:
        dict: User's effective quotas
    """
    # Start with defaults
    quotas = DEFAULT_USER_QUOTAS.copy()

    # TODO: Check for per-user overrides in UserQuota model
    # This allows admins to adjust individual user quotas
    # try:
    #     user_quota = UserQuota.objects.get(user=user)
    #     quotas = user_quota.to_dict()
    # except UserQuota.DoesNotExist:
    #     pass

    return quotas
