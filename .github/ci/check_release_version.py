"""Fail closed unless the checked-out tag matches the declared package version."""

import argparse
import os
import re
import subprocess
import tomllib
from pathlib import Path

VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?\Z")


def check_release(root: Path, tag: str) -> bool:
    """Validate canonical tag/version and checkout identity; return prerelease."""
    with (root / "pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError(
            "Package version must use canonical release/prerelease spelling"
        )
    if tag != f"v{version}":
        raise ValueError("Release tag does not match pyproject.toml version")

    def revision(ref: str) -> str:
        return subprocess.check_output(
            ["git", "rev-parse", "--verify", ref], cwd=root, text=True
        ).strip()

    if revision(f"refs/tags/{tag}^{{commit}}") != revision("HEAD^{commit}"):
        raise ValueError("Checkout does not match the release tag commit")
    return bool(re.search(r"(?:a|b|rc)\d+$", version))


def main() -> None:
    """Check the current checkout and emit GitHub's prerelease output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    arguments = parser.parse_args()
    prerelease = check_release(Path.cwd(), arguments.tag)
    result = f"prerelease={str(prerelease).lower()}\n"
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(result)
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
