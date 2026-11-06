"""Run the canonical resolver only in the owned preparation container."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run(spec):
    environment = dict(os.environ)
    environment.pop("UV_SYSTEM_PYTHON", None)
    environment["UV_CACHE_DIR"] = "/preflight/cache"
    # SCM backends sanitize GIT_* configuration variables. Only these NEW
    # owned clones are aligned with the build identity; serving roots stay RO.
    # Target.close restores ownership after both installation and probing.
    for target in spec["sources"]:
        os.chown(target, os.getuid(), os.getgid())
        os.chown(Path(target) / ".git", os.getuid(), os.getgid())
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--system",
            "--link-mode=copy",
            *[
                argument
                for target, row in spec["sources"].items()
                for argument in ("--editable", target + row["extras"])
            ],
        ],
        env=environment,
        check=True,
    )
    subprocess.run(["uv", "pip", "check", "--system"], env=environment, check=True)


if __name__ == "__main__":
    run(json.load(sys.stdin))
