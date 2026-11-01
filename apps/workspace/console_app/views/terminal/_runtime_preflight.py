"""Reject unconfigured compute paths before a terminal allocates resources."""

from __future__ import annotations

import posixpath
from pathlib import PurePosixPath


class TerminalConfigurationError(ValueError):
    """The service cannot yet provide an isolated terminal runtime."""


def validate_terminal_host_paths(container_path: str, user_data_root: str) -> None:
    """Validate declarations without assuming compute paths exist in Docker.

    SLURM executes these paths on a compute node. A valid remote path need
    not be mounted into Django, but sample placeholders and host root are
    never usable terminal boundaries.
    """
    for label, value in (
        ("compute image", container_path),
        ("workspace storage", user_data_root),
    ):
        raw = str(value).strip()
        path = PurePosixPath(posixpath.normpath(raw))
        placeholder = str(path).lstrip("/").split("/")[:2] == ["path", "to"]
        if (
            not raw
            or not path.is_absolute()
            or path == PurePosixPath("/")
            or placeholder
        ):
            raise TerminalConfigurationError(
                f"Terminal {label} is not configured on this service."
            )
