"""Operator-controlled maintenance state, independent of Django and user storage."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_MESSAGE = (
    "SciTeX is temporarily unavailable for maintenance. Please try again later."
)


@dataclass(frozen=True)
class MaintenanceState:
    enabled: bool = False
    message: str = DEFAULT_MESSAGE
    retry_after: int = 300
    valid: bool = True


def _validated(payload: object) -> MaintenanceState:
    if not isinstance(payload, dict) or type(payload.get("enabled")) is not bool:
        raise ValueError("Maintenance state requires a boolean enabled field.")
    message = payload.get("message", DEFAULT_MESSAGE)
    retry_after = payload.get("retry_after", 300)
    if not isinstance(message, str) or not message.strip() or len(message) > 512:
        raise ValueError("Maintenance message must contain 1–512 characters.")
    message.encode("utf-8")
    if type(retry_after) is not int or not 1 <= retry_after <= 86400:
        raise ValueError("Retry interval must be an integer from 1 to 86400 seconds.")
    return MaintenanceState(payload["enabled"], message, retry_after)


def read_state(path: str | Path | None) -> MaintenanceState:
    """Read a small trusted local flag; malformed/unreadable state closes admission."""
    if not path:
        return MaintenanceState()
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("Maintenance state must be a regular file.")
            raw = os.read(descriptor, 4097)
        finally:
            os.close(descriptor)
        if len(raw) > 4096:
            raise ValueError("Maintenance state is too large.")
        return _validated(json.loads(raw))
    except FileNotFoundError:
        return MaintenanceState()
    except (OSError, ValueError, UnicodeError):
        return MaintenanceState(enabled=True, valid=False)


def write_state(
    path: str | Path,
    *,
    enabled: bool,
    message: str = DEFAULT_MESSAGE,
    retry_after: int = 300,
) -> MaintenanceState:
    """Atomically publish state in an operator-owned directory on local storage."""
    state = _validated(
        {"enabled": enabled, "message": message, "retry_after": retry_after}
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=".maintenance-",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(
                {key: value for key, value in asdict(state).items() if key != "valid"},
                stream,
                ensure_ascii=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return state
