"""Retain failed installer output privately without changing its deadline."""

import json
import os
import subprocess
import tempfile

from preflight_targets import TargetUnreachable


def _private_log(stdout, stderr):
    descriptor, path = tempfile.mkstemp(
        prefix="scitex-hub-preflight-", suffix=".private.log"
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(stdout or b"")
        stream.write(stderr or b"")
    return path


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
