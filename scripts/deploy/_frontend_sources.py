"""Prepare immutable frontend source inputs from installed release identities."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata as metadata
import json
import re
import subprocess
import tomllib
import urllib.request
import zipfile
from pathlib import Path

VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?\Z")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(root: Path | None, *arguments: str) -> str:
    command = ["git", "-c", "core.hooksPath=/dev/null"]
    if root is not None:
        command += ["-C", str(root)]
    return subprocess.check_output([*command, *arguments], text=True).strip()


def installed_release(name: str) -> str:
    """Reject editable/source-directory fallbacks in the production input graph."""
    dist = metadata.distribution(name)
    direct = dist.read_text("direct_url.json")
    if direct and "dir_info" in json.loads(direct):
        raise ValueError(
            "Baked frontend inputs require installed wheels, not source installs"
        )
    if not VERSION.fullmatch(dist.version):
        raise ValueError("Frontend input is not a canonical public release")
    return dist.version


def source_version(root: Path) -> tuple[str, str]:
    """Read static project identity or a literal Hatch version; never import it."""
    config = tomllib.loads((root / "pyproject.toml").read_text())
    project = config["project"]
    version = project.get("version")
    if version is None:
        relative = (
            config.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
        )
        if not isinstance(relative, str):
            raise ValueError("Unproven source version declaration")
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Source version file escapes its checkout")
        values = [
            node.value.value
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets
            )
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ]
        if len(values) != 1:
            raise ValueError("Source version is not one literal __version__")
        version = values[0]
    return project["name"], version


def clone_release(
    url: str, tag: str, destination: Path, name: str, version: str
) -> dict:
    """Clone an exact public tag, then verify before executing any project code."""
    if destination.exists() or destination.is_symlink():
        raise ValueError(
            f"Refusing to overwrite existing frontend source: {destination}"
        )
    refs = git(
        None,
        "ls-remote",
        "--exit-code",
        url,
        f"refs/tags/{tag}",
        f"refs/tags/{tag}^{{}}",
    )
    entries = dict(line.split()[::-1] for line in refs.splitlines())
    expected = entries.get(f"refs/tags/{tag}^{{}}", entries.get(f"refs/tags/{tag}"))
    if not expected or not re.fullmatch(r"[a-f0-9]{40}", expected):
        raise ValueError("Release tag has no unambiguous Git commit")
    subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "clone",
            "--depth",
            "1",
            "--branch",
            tag,
            "--",
            url,
            str(destination),
        ],
        check=True,
    )
    actual = git(destination, "rev-parse", "HEAD")
    if actual != expected:
        raise ValueError("Release tag changed while cloning")
    source_name, source_release = source_version(destination)
    if (
        source_name.replace("_", "-").lower() != name.replace("_", "-").lower()
        or source_release != version
    ):
        raise ValueError("Frontend source version differs from installed distribution")
    if git(destination, "status", "--porcelain"):
        raise ValueError("Frontend source is modified before dependency installation")
    return {
        "distribution": name,
        "version": version,
        "tag": tag,
        "commit": actual,
        "tree": git(destination, "rev-parse", "HEAD^{tree}"),
    }


def installed_npm_package(distribution: str) -> Path:
    """Locate the wheel-owned public npm package without importing product code."""
    installed_release(distribution)
    dist = metadata.distribution(distribution)
    package = distribution.replace("-", "_")
    relative = f"{package}/package.json"
    if relative not in {str(p) for p in dist.files or ()}:
        raise ValueError(f"{distribution} has no published frontend package")
    root = Path(dist.locate_file(relative)).parent.resolve()
    if json.loads((root / "package.json").read_text()).get(
        "name"
    ) != "@scitex/" + distribution.removeprefix("scitex-"):
        raise ValueError("Published npm package identity differs from distribution")
    return root


def verify_sdk_wheel(wheel: Path, digest: str) -> dict:
    """Match every installed SDK namespace member to the verified public wheel."""
    if sha256(wheel) != digest:
        raise ValueError("SDK wheel digest mismatch")
    dist = metadata.distribution("scitex-sdk")
    members = {}
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate wheel members")
        for name in names:
            if not name.startswith("scitex_sdk/") or name.endswith("/"):
                continue
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe wheel member")
            expected = hashlib.sha256(archive.read(name)).hexdigest()
            path = Path(dist.locate_file(name))
            if path.is_symlink() or not path.is_file() or sha256(path) != expected:
                raise ValueError(f"Installed SDK differs from public wheel: {name}")
            members[name] = expected
    if not members:
        raise ValueError("SDK wheel has no namespace payload")
    return {
        "distribution": "scitex-sdk",
        "version": dist.version,
        "wheel_filename": wheel.name,
        "wheel_sha256": digest,
        "namespace_sha256": hashlib.sha256(
            json.dumps(members, sort_keys=True).encode()
        ).hexdigest(),
    }


def public_sdk_identity(directory: Path) -> dict:
    version = installed_release("scitex-sdk")
    if not VERSION.fullmatch(version):
        raise ValueError("SDK is not a canonical public release")
    with urllib.request.urlopen(
        f"https://pypi.org/pypi/scitex-sdk/{version}/json", timeout=30
    ) as response:
        release = json.load(response)
    wheels = [
        row for row in release["urls"] if row["filename"].endswith("-py3-none-any.whl")
    ]
    if len(wheels) != 1:
        raise ValueError("SDK public wheel identity is ambiguous")
    row = wheels[0]
    target = directory / row["filename"]
    with urllib.request.urlopen(row["url"], timeout=60) as response:
        target.write_bytes(response.read())
    return verify_sdk_wheel(target, row["digests"]["sha256"])


def prepare_sources(app_root: Path, records: Path) -> dict:
    """Prepare the registry's six pinned releases and wheel-derived peer layouts."""
    app_root = app_root.resolve()
    registry = json.loads((app_root / ".scitex-apps.json").read_text())
    records.mkdir(parents=True, exist_ok=False)
    if (app_root / ".apps").exists() and any((app_root / ".apps").iterdir()):
        raise ValueError("Unreviewed .apps source inputs must not enter a baked build")
    sources = []
    for row in registry["apps"]:
        name = row["pip_package"]
        version = installed_release(name)
        if not VERSION.fullmatch(version) or row["name"] != name:
            raise ValueError("A frontend input is not a canonical installed release")
        sources.append(
            clone_release(
                row["git_url"],
                f"v{version}",
                app_root.parent / row["name"],
                name,
                version,
            )
        )
    peers = [
        {
            "distribution": name,
            "version": metadata.version(name),
            "package_json_sha256": sha256(installed_npm_package(name) / "package.json"),
        }
        for name in ("scitex-sdk", "scitex-live-paper")
    ]
    sdk = public_sdk_identity(records)
    result = {
        "sources": sources,
        "peers": peers,
        "sdk": sdk,
        "registry_sha256": sha256(app_root / ".scitex-apps.json"),
    }
    (records / "inputs.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def npm_inputs(app_root: Path, inputs: dict) -> tuple[list[Path], dict[str, Path]]:
    """Find root/bridge npm packages only in the six verified source checkouts."""
    manifests = [app_root / "package.json"]
    providers = {}
    for row in inputs["sources"]:
        root = app_root.parent / row["distribution"]
        candidates = [root / "package.json"]
        manifest = (
            root
            / "src"
            / row["distribution"].replace("-", "_")
            / "_django/manifest.json"
        )
        if manifest.is_file():
            bridge = json.loads(manifest.read_text()).get("bridge")
            if bridge:
                frontend = manifest.parent / "frontend"
                entry = (frontend / bridge["entry"]).resolve()
                if not entry.is_relative_to(frontend.resolve()) or not entry.is_file():
                    raise ValueError("Declared frontend bridge entry is unavailable")
                candidates.append(frontend / "package.json")
        for candidate in candidates:
            if not candidate.is_file():
                if candidate.parent.name == "frontend":
                    raise ValueError(
                        "Frontend bridge has no npm dependency declaration"
                    )
                continue
            package_name = json.loads(candidate.read_text())["name"]
            if package_name in providers:
                raise ValueError("Ambiguous frontend npm provider")
            providers[package_name] = candidate.parent
            manifests.append(candidate)
    for row in inputs["peers"]:
        root = installed_npm_package(row["distribution"])
        name = json.loads((root / "package.json").read_text())["name"]
        if name in providers:
            raise ValueError("Source checkout shadows the installed frontend provider")
        providers[name] = root
    return manifests, providers


def bind_file_dependencies(package_json: Path, providers: dict[str, Path]) -> dict:
    """Resolve existing file: dependencies to verified source or wheel providers."""
    import os

    before = sha256(package_json)
    package = json.loads(package_json.read_text())
    bindings = {}
    for group in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, value in package.get(group, {}).items():
            if not isinstance(value, str) or not value.startswith("file:"):
                continue
            if name not in providers:
                raise ValueError(f"Unproven local npm provider: {name}")
            target = providers[name].resolve()
            relative = os.path.relpath(target, package_json.parent)
            replacement = f"file:{relative}"
            bindings[name] = {"declared": value, "resolved": replacement}
            package[group][name] = replacement
    if bindings:
        package_json.write_text(json.dumps(package, indent=2) + "\n")
    # npm can retain a tagged lock's stale local-link resolved path even after
    # package-lock-only updates the root dependency. Regenerate only manifests
    # with admitted local providers; preserve the original lock identity first.
    lock = package_json.with_name("package-lock.json")
    original_lock = None
    if bindings and (lock.exists() or lock.is_symlink()):
        if lock.is_symlink() or not lock.is_file():
            raise ValueError("Local dependency lock is not a regular owned build file")
        original_lock = sha256(lock)
        lock.unlink()
    return {
        "original_lock_sha256": original_lock,
        "package_json": str(package_json),
        "before_sha256": before,
        "after_sha256": sha256(package_json),
        "bindings": bindings,
    }
