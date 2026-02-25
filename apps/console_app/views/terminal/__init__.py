"""
Terminal Views Module
Provides PTY terminal functionality via WebSocket

Backward Compatibility:
    from apps.console_app.terminal_views import TerminalConsumer
    → from apps.console_app.views.terminal import TerminalConsumer
"""

from .config import (
    BASE_CONTAINER_PATH,
    HOST_MOUNTS,
    HOST_TEXLIVE_PREFIX,
    SLURM_CONTAINER_PATH,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
    SLURM_USER_DATA_ROOT,
    USER_DATA_ROOT,
)
from .consumer import TerminalConsumer

__all__ = [
    "TerminalConsumer",
    "BASE_CONTAINER_PATH",
    "USER_DATA_ROOT",
    "SLURM_PARTITION",
    "SLURM_TIME_LIMIT",
    "SLURM_CPUS",
    "SLURM_MEMORY_GB",
    "SLURM_CONTAINER_PATH",
    "SLURM_USER_DATA_ROOT",
    "HOST_MOUNTS",
    "HOST_TEXLIVE_PREFIX",
]

# EOF
