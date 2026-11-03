#!/usr/bin/env python3
"""Build the production frontend once from installed release-matched inputs."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import subprocess
from pathlib import Path

from _frontend_artifact import seal
from _frontend_sources import (
    bind_file_dependencies,
    installed_npm_package,
    npm_inputs,
    prepare_sources,
    sha256,
    verify_sdk_wheel,
)


def build(app_root: Path, artifact: Path) -> dict:
    """No editable/pip install occurs here; all frontend failures abort the build."""
    app_root = app_root.resolve()
    before = {dist.metadata["Name"]: dist.version for dist in metadata.distributions()}
    records = artifact.with_name(artifact.name + "-inputs")
    inputs = prepare_sources(app_root, records)
    manifests, providers = npm_inputs(app_root, inputs)
    inputs["npm_bindings"] = [
        bind_file_dependencies(path, providers) for path in manifests
    ]
    environment = os.environ.copy()
    environment["SCITEX_SDK_ROOT"] = str(installed_npm_package("scitex-sdk"))
    ui = app_root.parent / "scitex-ui/src/scitex_ui/static/scitex_ui"
    if not ui.is_dir():
        raise ValueError("Verified UI source has no static frontend namespace")
    environment["SCITEX_UI_STATIC"] = str(ui)
    # Create full lockfiles from these exact local providers, then install their
    # frozen closures. No optional dependency reduction or ignored npm failures.
    for package in [*manifests[1:], manifests[0]]:
        for arguments in (
            ["install", "--package-lock-only", "--no-audit", "--no-fund"],
            ["ci", "--no-audit", "--no-fund"],
        ):
            subprocess.run(
                ["npm", *arguments], cwd=package.parent, env=environment, check=True
            )
    subprocess.run(["npm", "run", "build"], cwd=app_root, env=environment, check=True)
    after = {dist.metadata["Name"]: dist.version for dist in metadata.distributions()}
    if after != before:
        raise ValueError("Frontend build changed the Python distribution graph")
    sdk = inputs["sdk"]
    verify_sdk_wheel(records / sdk["wheel_filename"], sdk["wheel_sha256"])
    inputs["npm_locks"] = {
        str(package.with_name("package-lock.json")): sha256(
            package.with_name("package-lock.json")
        )
        for package in manifests
    }
    inputs["python_versions"] = before
    (records / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    return seal(app_root, app_root / "staticfiles/vite", artifact, inputs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", type=Path, default=Path("/opt/scitex-frontend"))
    args = parser.parse_args()
    build(args.app_root, args.artifact)


if __name__ == "__main__":
    main()
