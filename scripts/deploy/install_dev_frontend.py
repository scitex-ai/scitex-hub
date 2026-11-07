#!/usr/bin/env python3
"""Install mounted npm providers before the application that links to them."""

import json
import subprocess
import sys
from pathlib import Path


def install_workspace(root: Path) -> None:
    """Install each declared local provider once, including its own graph."""
    visited: set[Path] = set()
    ordered: list[Path] = []

    def visit(directory: Path) -> None:
        directory = directory.resolve(strict=True)
        if directory in visited:
            return
        visited.add(directory)
        package = json.loads((directory / "package.json").read_text())
        for group in (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
        ):
            for reference in package.get(group, {}).values():
                if reference.startswith("file:"):
                    visit(directory / reference.removeprefix("file:"))
        ordered.append(directory)

    visit(root)
    for directory in ordered:
        subprocess.run(
            [
                "npm",
                "install",
                "--include=dev",
                "--include=optional",
                "--no-audit",
                "--no-fund",
            ],
            cwd=directory,
            check=True,
        )
        subprocess.run(["npm", "ls", "--depth=0"], cwd=directory, check=True)


if __name__ == "__main__":
    install_workspace(Path(sys.argv[1]))
