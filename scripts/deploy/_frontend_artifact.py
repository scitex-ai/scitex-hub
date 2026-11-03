#!/usr/bin/env python3
"""Seal, verify and install a complete baked Vite closure without network/builds."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import shutil
import stat
import tempfile
import tomllib
from pathlib import Path, PurePosixPath

SCHEMA = "scitex-hub.baked-frontend/v1"
MANIFEST = ".vite/manifest.json"
SKIP = {"node_modules", "__pycache__", ".git"}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative(value: str) -> Path:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or ":" in value
        or str(path) != value
    ):
        raise ValueError("Unsafe frontend artifact member")
    return Path(value)


def files(root: Path) -> dict[str, str]:
    result = {}
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Frontend artifact root is not a regular directory")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Frontend artifact contains a symbolic link")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
        elif not path.is_dir():
            raise ValueError("Frontend artifact contains a special file")
    return result


def source_inputs(root: Path) -> dict[str, str]:
    paths = [
        root / name
        for name in (
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "vite.config.ts",
            "vite.entries.ts",
            ".scitex-apps.json",
        )
    ]
    for base in (root / "static", root / "apps"):
        if not base.is_dir():
            continue
        paths += [
            path
            for path in base.rglob("*")
            if path.suffix in {".ts", ".tsx", ".js", ".jsx", ".css"}
            and not SKIP.intersection(path.relative_to(base).parts)
            and not path.is_relative_to(root / "static/vite")
        ]
    result = {}
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or symbolic Hub frontend input")
        result[path.relative_to(root).as_posix()] = digest(path)
    return result


def sdk_namespace() -> dict[str, str]:
    dist = metadata.distribution("scitex-sdk")
    root = Path(dist.locate_file("scitex_sdk"))
    return {
        f"scitex_sdk/{name}": value
        for name, value in files_without_bytecode(root).items()
    }


def files_without_bytecode(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("SDK namespace contains a symbolic link")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def validate_manifest(root: Path, inventory: dict[str, str]) -> None:
    if MANIFEST not in inventory or len(inventory) < 2:
        raise ValueError("Baked frontend has no complete Vite manifest")
    manifest = json.loads((root / MANIFEST).read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("Vite manifest is empty or malformed")
    for entry in manifest.values():
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise ValueError("Invalid Vite entry")
        for value in [entry["file"], *entry.get("css", []), *entry.get("assets", [])]:
            relative(value)
            if value not in inventory:
                raise ValueError(f"Vite manifest references an absent member: {value}")
        for key in [*entry.get("imports", []), *entry.get("dynamicImports", [])]:
            if key not in manifest:
                raise ValueError("Vite manifest references an absent chunk entry")


def seal(app_root: Path, vite: Path, artifact: Path, inputs: dict) -> dict:
    """Copy the finished build into a separate immutable image-owned artifact."""
    if artifact.exists() or artifact.is_symlink():
        raise ValueError("Refusing to replace an existing baked artifact")
    inventory = files(vite)
    validate_manifest(vite, inventory)
    artifact.mkdir(parents=True)
    shutil.copytree(vite, artifact / "vite")
    sdk = sdk_namespace()
    namespace_hash = hashlib.sha256(
        json.dumps(sdk, sort_keys=True).encode()
    ).hexdigest()
    if namespace_hash != inputs["sdk"]["namespace_sha256"]:
        raise ValueError("SDK changed after its public wheel verification")
    receipt = {
        "schema": SCHEMA,
        "hub_version": tomllib.loads((app_root / "pyproject.toml").read_text())[
            "project"
        ]["version"],
        "hub_inputs": source_inputs(app_root),
        "inputs": inputs,
        "sdk_namespace": sdk,
        "files": inventory,
    }
    (artifact / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    for path in artifact.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    artifact.chmod(0o755)
    return receipt


def verify(artifact: Path, app_root: Path) -> dict:
    """Verify owner, complete payload, source/lock and current SDK before copying."""
    owner = Path(__file__).stat().st_uid
    for path in [artifact, *artifact.rglob("*")]:
        info = path.lstat()
        if (
            path.is_symlink()
            or info.st_uid != owner
            or stat.S_IMODE(info.st_mode) & 0o022
        ):
            raise ValueError(
                "Baked artifact is not owned and protected by the trusted tool owner"
            )
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError("Baked artifact contains a nonregular member")
    receipt_path = artifact / "receipt.json"
    fd = os.open(receipt_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024 * 1024:
            raise ValueError("Invalid baked receipt")
        chunks = []
        remaining = 8 * 1024 * 1024 + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("Oversized baked receipt")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("Baked receipt changed while reading")
        receipt = json.loads(data)
    finally:
        os.close(fd)
    if receipt.get("schema") != SCHEMA:
        raise ValueError("Missing or unsupported baked receipt schema")
    expected = receipt.get("files")
    if not isinstance(expected, dict) or files(artifact / "vite") != expected:
        raise ValueError("Baked frontend is partial, tampered or has unexpected files")
    for name in expected:
        relative(name)
    validate_manifest(artifact / "vite", expected)
    if receipt["hub_inputs"] != source_inputs(app_root):
        raise ValueError("Baked frontend belongs to different Hub source/lock inputs")
    if receipt["sdk_namespace"] != sdk_namespace():
        raise ValueError("Current SDK differs from the baked frontend provider")
    if receipt["inputs"]["sdk"]["version"] != metadata.version("scitex-sdk"):
        raise ValueError("Current SDK metadata differs from baked frontend")
    for row in [*receipt["inputs"]["sources"], *receipt["inputs"]["peers"]]:
        if metadata.version(row["distribution"]) != row["version"]:
            raise ValueError("Current Python/frontend release identities differ")
    current = {dist.metadata["Name"]: dist.version for dist in metadata.distributions()}
    if receipt["inputs"]["python_versions"] != current:
        raise ValueError("Current Python graph differs from the baked frontend graph")
    return receipt


def destination_path(root: Path, name: str) -> Path:
    path = root / relative(name)
    for member in [root, *path.parents]:
        if member.is_symlink():
            raise ValueError("Frontend destination must not contain symbolic links")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Frontend destination member is not regular")
    return path


def install(artifact: Path, app_root: Path, destination: Path) -> dict:
    """Preserve old hashed chunks; publish the new complete manifest last."""
    receipt = verify(artifact, app_root)
    names = [name for name in sorted(receipt["files"]) if name != MANIFEST] + [MANIFEST]
    # Reject an unsafe target before changing any existing member.
    for name in names:
        destination_path(destination, name)
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = destination_path(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".baked-", dir=target.parent)
        try:
            with (
                os.fdopen(fd, "wb") as output,
                (artifact / "vite" / name).open("rb") as source,
            ):
                shutil.copyfileobj(source, output)
                output.flush()
                os.fsync(output.fileno())
                os.fchmod(output.fileno(), 0o644)
            if digest(Path(temporary)) != receipt["files"][name]:
                raise ValueError("Copied frontend member failed its digest check")
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    for name, value in receipt["files"].items():
        if digest(destination / name) != value:
            raise ValueError("Installed frontend member changed during publication")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, default=Path("/app"))
    parser.add_argument("--artifact", type=Path, default=Path("/opt/scitex-frontend"))
    parser.add_argument(
        "--destination", type=Path, default=Path("/app/staticfiles/vite")
    )
    arguments = parser.parse_args()
    if Path(__file__).stat().st_uid != 0:
        raise ValueError("Production baked frontend installer must be root-owned")
    install(arguments.artifact, arguments.app_root, arguments.destination)


if __name__ == "__main__":
    main()
