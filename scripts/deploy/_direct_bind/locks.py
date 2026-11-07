"""Fingerprint npm's generated locks without accepting other source edits."""

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath


def fingerprints(source):
    raw = subprocess.check_output(
        [
            "git",
            "-C",
            str(source),
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        stderr=subprocess.PIPE,
        timeout=60,
    )
    result = {}
    for entry in raw.decode("utf-8", "surrogateescape").split("\0"):
        if not entry:
            continue
        status, relative = entry[:2], entry[3:]
        path = PurePosixPath(relative)
        message = "commit development source changes before a container recreation"
        if (
            status not in (" M", "??")
            or path.is_absolute()
            or ".." in path.parts
            or path.name != "package-lock.json"
        ):
            raise ValueError(message)
        manifest = path.with_name("package.json")
        tracked = subprocess.run(
            [
                "git",
                "-C",
                str(source),
                "ls-files",
                "--error-unmatch",
                "--",
                str(manifest),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        if tracked.returncode:
            raise ValueError(message)
        payload = read_payload(Path(source) / relative)
        if not isinstance(json.loads(payload), dict):
            raise ValueError("generated npm lock is not a JSON object")
        result[relative] = {
            "status": status,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return result


def read_payload(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 64 * 1024**2:
            raise ValueError("generated npm lock is not a bounded regular file")
        payload = stream.read(64 * 1024**2 + 1)
    if len(payload) > 64 * 1024**2:
        raise ValueError("generated npm lock grew beyond the supported bound")
    return payload
