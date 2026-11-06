"""Payload run only in the owned prospective-profile container."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run(spec):
    # The image supplies system dependencies; real editable installs shadow them
    # in a normal venv. No distribution metadata or version is fabricated.
    root = Path("/preflight")
    environment = dict(os.environ)
    environment.pop("UV_SYSTEM_PYTHON", None)
    # setuptools-scm deliberately sanitizes GIT_* configuration variables.
    # These are NEW owned snapshots, never original serving repositories.
    # Align the clone roots with the build identity instead of trusting '*'.
    for target in spec["sources"]:
        os.chown(target, os.getuid(), os.getgid())
        os.chown(Path(target) / ".git", os.getuid(), os.getgid())
    python = root / "env/bin/python"
    commands = [
        [
            "uv",
            "venv",
            "--seed",
            "--system-site-packages",
            "--python",
            sys.executable,
            str(root / "env"),
        ],
        [
            str(python),
            "-m",
            "pip",
            "install",
            *[
                argument
                for target, row in spec["sources"].items()
                for argument in ("--editable", target + row["extras"])
            ],
        ],
        [str(python), "-m", "pip", "check"],
    ]
    try:
        for command in commands:
            subprocess.run(command, env=environment, check=True)
    finally:
        # Build backends may write egg-info into these NEW owned copies.
        # Do not follow links or change original Git objects/source directories.
        for directory, names, files in os.walk("/preflight-sources", followlinks=False):
            for name in names + files:
                os.lchown(os.path.join(directory, name), spec["uid"], spec["gid"])
            os.lchown(directory, spec["uid"], spec["gid"])


if __name__ == "__main__":
    run(json.load(sys.stdin))
