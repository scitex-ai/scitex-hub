"""
Active terminal connection registry.

Tracks WebSocket terminal connections per user so the Jobs API
can report active terminal sessions alongside SLURM jobs.
"""

from __future__ import annotations

# {username: {channel_name, ...}}
_active_terminals: dict[str, set[str]] = {}


def get_active_terminal_count(username: str) -> int:
    """Return number of active terminal WebSocket connections for a user."""
    return len(_active_terminals.get(username, set()))


def register_terminal(username: str, channel_name: str) -> None:
    """Register an active terminal connection."""
    _active_terminals.setdefault(username, set()).add(channel_name)


def unregister_terminal(username: str, channel_name: str) -> None:
    """Unregister a terminal connection."""
    if username in _active_terminals:
        _active_terminals[username].discard(channel_name)
        if not _active_terminals[username]:
            del _active_terminals[username]


# EOF
