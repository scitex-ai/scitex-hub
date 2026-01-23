"""
Terminal Views Module
Provides PTY terminal functionality via WebSocket

Backward Compatibility:
    from apps.code_app.terminal_views import TerminalConsumer
    → from apps.code_app.views.terminal import TerminalConsumer
"""

from .consumer import TerminalConsumer
from .config import (
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
