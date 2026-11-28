"""Retain failed installer output privately without changing its deadline."""

import json
import os
import subprocess
import tempfile
import traceback

from preflight_targets import TargetUnreachable


def _private_log(stdout, stderr):
    descriptor, path = tempfile.mkstemp(
        prefix="scitex-hub-preflight-", suffix=".private.log"
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(stdout or b"")
        stream.write(stderr or b"")
    return path


def private_exception_log(*errors):
    """Keep preparation/cleanup causes out of public deployment diagnostics."""
    chunks = []
    for error in errors:
        chunks.append("".join(traceback.format_exception(error)).encode())
        for attribute in ("stdout", "stderr"):
            value = getattr(error, attribute, None)
            if value:
                chunks.append(value.encode() if isinstance(value, str) else value)
    return _private_log(b"\n".join(chunks), b"")


def run_install(command, specification, timeout):
    """Refuse failed/expired installs; expose only their private log path."""
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(specification).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        path = _private_log(error.stdout, error.stderr)
        raise TargetUnreachable(
            "normal prospective editable installation or dependency check "
            "exceeded its deadline; private diagnostics: {0}; "
            "no deployment was changed".format(path)
        ) from None
    if completed.returncode:
        path = _private_log(completed.stdout, completed.stderr)
        raise TargetUnreachable(
            "normal prospective editable installation or dependency check failed; "
            "private diagnostics: {0}; no deployment was changed".format(path)
        )
