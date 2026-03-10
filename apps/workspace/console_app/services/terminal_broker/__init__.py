"""Terminal broker package — PTY management outside Daphne's asyncio loop."""

from .allocation import Allocation, AllocationState
from .broker import SHARED_ALLOCATION, SOCKET_PATH, TerminalBroker, main
from .session import BasePTY, TerminalSession
from .shell import Shell

__all__ = [
    "TerminalBroker",
    "TerminalSession",
    "Allocation",
    "AllocationState",
    "Shell",
    "SOCKET_PATH",
    "main",
]

# EOF
