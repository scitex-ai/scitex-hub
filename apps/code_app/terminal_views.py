"""
Terminal Views - Backward Compatibility Wrapper

This file maintains backward compatibility for existing imports.
Actual implementation has been moved to apps/code_app/views/terminal/

Migration:
    Old: from apps.code_app.terminal_views import TerminalConsumer
    New: from apps.code_app.views.terminal import TerminalConsumer
"""

from apps.code_app.views.terminal import (
    TerminalConsumer,
    BASE_CONTAINER_PATH,
    USER_DATA_ROOT,
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_CONTAINER_PATH,
    SLURM_USER_DATA_ROOT,
)

__all__ = [
    'TerminalConsumer',
    'BASE_CONTAINER_PATH',
    'USER_DATA_ROOT',
    'SLURM_PARTITION',
    'SLURM_TIME_LIMIT',
    'SLURM_CPUS',
    'SLURM_MEMORY_GB',
    'SLURM_CONTAINER_PATH',
    'SLURM_USER_DATA_ROOT',
]

# EOF
