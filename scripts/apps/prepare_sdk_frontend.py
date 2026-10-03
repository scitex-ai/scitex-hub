#!/usr/bin/env python3
"""Pack the selected Python SDK frontend before Hub's ordinary npm install."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

MINIMUM = (0, 3, 0)
PACKAGE = "@scitex/sdk"
STATIC_ROOT = "ui/static/scitex_sdk/ui"


def _release_version(value: str) -> tuple[int, int, int]:
    """Require a stable npm-compatible release at the declared frontend floor."""
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError("SDK frontend requires a stable major.minor.patch release")
    result = tuple(int(part) for part in value.split("."))
    if result < MINIMUM:
        raise ValueError("SDK frontend requires scitex-sdk>=0.3.0")
    return result


def _owned_package(distribution, directory: Path) -> None:
    """Bind the imported helper to its wheel or declared editable distribution."""
    files = distribution.files or ()
    for item in files:
        if str(item).replace("\\", "/") == "scitex_sdk/__init__.py":
            if Path(distribution.locate_file(item)).resolve().parent == directory:
                return
    direct = distribution.read_text("direct_url.json")
    if direct:
        source = json.loads(direct)
        url = urlparse(source.get("url", ""))
        if source.get("dir_info", {}).get("editable") is True and url.scheme == "file" and not url.netloc:
            root = Path(unquote(url.path)).resolve()
            if (root / "src/scitex_sdk").resolve() == directory:
                return
    raise ValueError("Selected SDK distribution does not own the imported frontend")


def _frontend_files(directory: Path, metadata: dict) -> list[Path]:
    if metadata.get("name") != PACKAGE:
        raise ValueError("Selected SDK frontend package is not @scitex/sdk")
    exports = metadata.get("exports", {})
    required = {
        "./ui": "./ui/static/scitex_sdk/ui/react/index.ts",
        "./ui/ts": "./ui/static/scitex_sdk/ui/ts/index.ts",
        "./ui/css/*": "./ui/static/scitex_sdk/ui/css/*",
    }
    if any(exports.get(key) != value for key, value in required.items()):
        raise ValueError("Selected SDK lacks the canonical frontend exports")
    if f"{STATIC_ROOT}/**" not in metadata.get("files", ()):
        raise ValueError("Selected SDK does not package its canonical UI assets")
    expected = [directory / "package.json"]
    expected.extend(path for path in (directory / STATIC_ROOT).rglob("*") if path.is_file())
    for name in [f"{STATIC_ROOT}/css/app.css", required["./ui"][2:], required["./ui/ts"][2:]]:
        if not (directory / name).is_file():
            raise ValueError(f"Selected SDK frontend file is missing: {name}")
    if any(not path.resolve().is_relative_to(directory) for path in expected):
        raise ValueError("SDK frontend assets escape the selected package")
    return expected


def selected_frontend() -> tuple[Path, dict, list[Path]]:
    distribution = importlib.metadata.distribution("scitex-sdk")
    _release_version(distribution.version)
    sdk = importlib.import_module("scitex_sdk")
    directory = Path(sdk.get_frontend_package_dir()).resolve()
    if Path(sdk.__file__).resolve().parent != directory:
        raise ValueError("SDK helper and imported package disagree")
    _owned_package(distribution, directory)
    metadata = json.loads((directory / "package.json").read_text())
    if metadata.get("version") != distribution.version:
        raise ValueError("SDK frontend version differs from the selected Python distribution")
    return directory, metadata, _frontend_files(directory, metadata)


def verify_archive(archive: Path, directory: Path, expected: list[Path]) -> None:
    """Require a complete regular-file frontend archive with exact source bytes."""
    included = set()
    with tarfile.open(archive, "r:gz") as packed:
        for member in packed:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or not name.parts or name.parts[0] != "package":
                raise ValueError("SDK npm archive contains an unsafe path")
            if member.isdir():
                continue
            if not member.isfile() or member.name in included:
                raise ValueError("SDK npm archive must contain unique regular files")
            original = directory.joinpath(*name.parts[1:])
            if not original.resolve().is_relative_to(directory) or not original.is_file():
                raise ValueError("SDK npm archive contains an unowned file")
            if packed.extractfile(member).read() != original.read_bytes():
                raise ValueError("SDK npm archive differs from selected frontend source")
            included.add(member.name)
    required = {"package/" + path.relative_to(directory).as_posix() for path in expected}
    if not required.issubset(included):
        raise ValueError("SDK npm archive omits selected frontend assets")


def prepare(project: Path) -> dict:
    directory, metadata, expected = selected_frontend()
    output = project / ".frontend-packages"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sdk-pack-", dir=output) as temporary:
        result = subprocess.run(
            ["npm", "pack", str(directory), "--ignore-scripts", "--json", "--pack-destination", temporary],
            check=True, capture_output=True, text=True, timeout=60,
        )
        packed = json.loads(result.stdout)
        if not isinstance(packed, list) or len(packed) != 1:
            raise ValueError("npm pack did not return exactly one SDK archive")
        name = packed[0].get("filename", "")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".tgz"):
            raise ValueError("npm pack returned an unsafe SDK archive filename")
        archive = Path(temporary) / name
        verify_archive(archive, directory, expected)
        if json.loads((directory / "package.json").read_text()) != metadata:
            raise ValueError("Selected SDK frontend changed during packing")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        os.replace(archive, output / "scitex-sdk.tgz")
    receipt = {"name": PACKAGE, "version": metadata["version"], "sha256": digest,
               "python": sys.executable, "selected_frontend": str(directory)}
    (output / "sdk-provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def verify_installed(project: Path) -> dict:
    """Refuse a stale or foreign npm frontend after ordinary npm resolution."""
    directory, metadata, expected = selected_frontend()
    installed = (project / "node_modules/@scitex/sdk").resolve()
    if not installed.is_relative_to(project.resolve()):
        raise ValueError("Installed SDK frontend escapes the consumer project")
    identities = {}
    for original in expected:
        relative = original.relative_to(directory)
        target = installed / relative
        if not target.is_file() or not target.resolve().is_relative_to(installed):
            raise ValueError(f"Installed SDK frontend is missing or unsafe: {relative}")
        data = target.read_bytes()
        if data != original.read_bytes():
            raise ValueError(f"Installed SDK frontend differs from selected Python SDK: {relative}")
        identities[relative.as_posix()] = hashlib.sha256(data).hexdigest()
    digest = hashlib.sha256(json.dumps(identities, sort_keys=True).encode()).hexdigest()
    return {"name": PACKAGE, "version": metadata["version"], "sha256": digest}


def main() -> int:
    try:
        if sys.argv[1:] not in ([], ["--verify-installed"]):
            raise ValueError("Usage: prepare_sdk_frontend.py [--verify-installed]")
        project = Path(__file__).resolve().parents[2]
        receipt = verify_installed(project) if sys.argv[1:] else prepare(project)
    except (ImportError, OSError, ValueError, AttributeError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f"ERROR: SDK frontend preparation refused: {error}", file=sys.stderr)
        return 1
    action = "Verified installed" if sys.argv[1:] else "Prepared"
    print(f"{action} {receipt['name']} {receipt['version']} ({receipt['sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
