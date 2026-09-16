#!/usr/bin/env python3
"""Fail unless this interpreter satisfies Hub's sibling dependency contract.

Run inside the completed production image.  Unlike Dockerfile-text checks this
reads installed distribution metadata, validates inter-package requirements,
and executes the explicit import surfaces in preflight_contract.json.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import stat
import sys
import sysconfig
import tomllib
from itertools import chain
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def sibling(name: str) -> bool:
    normalized = canonicalize_name(name)
    return normalized.startswith("scitex-") or normalized == "figrecipe"


def declarations() -> dict[str, list[Requirement]]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    groups = [data["project"]["dependencies"]]
    groups.extend(data["project"].get("optional-dependencies", {}).values())
    result: dict[str, list[Requirement]] = {}
    for raw in (item for group in groups for item in group):
        req = Requirement(raw)
        name = canonicalize_name(req.name)
        if sibling(name):
            result.setdefault(name, []).append(req)
    if not result:
        raise RuntimeError("parsed zero sibling declarations")
    return result


def requirement_applies(requirement: Requirement, active_extras: set[str]) -> bool:
    """Return whether a requirement applies in the installed image context."""
    if requirement.marker is None:
        return True
    contexts = active_extras or {""}
    return any(requirement.marker.evaluate({"extra": extra}) for extra in contexts)


def immutable_tree_errors(root: Path, required_uid: int = 0) -> list[str]:
    """Report entries an unprivileged application process could replace."""
    errors: list[str] = []
    inspected: set[Path] = set()

    def inspect(path: Path) -> None:
        if path in inspected:
            return
        inspected.add(path)
        try:
            info = path.lstat()
        except OSError as exc:
            errors.append(f"{path}: cannot inspect: {type(exc).__name__}: {exc}")
            return
        if info.st_uid != required_uid:
            errors.append(f"{path}: owner uid {info.st_uid}, expected {required_uid}")
        if not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022:
            errors.append(f"{path}: group/other-writable mode {oct(stat.S_IMODE(info.st_mode))}")
        if stat.S_ISLNK(info.st_mode):
            try:
                target = path.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                errors.append(f"{path}: invalid symlink: {type(exc).__name__}: {exc}")
                return
            for controlled_path in chain((target,), target.parents):
                inspect(controlled_path)
            if target.is_dir():
                for descendant in target.rglob("*"):
                    inspect(descendant)

    for path in chain((root,), root.rglob("*")):
        inspect(path)
    return errors


def runtime_immutability_errors() -> list[str]:
    """Verify Python packages and console scripts remain root-controlled."""
    roots = (
        Path(sysconfig.get_paths()["purelib"]),
        Path(sys.executable).resolve().parent,
    )
    return [error for root in roots for error in immutable_tree_errors(root)]


def verify() -> list[str]:
    errors: list[str] = []
    contract = json.loads((ROOT / "scripts/deploy/preflight_contract.json").read_text())
    active_extras = {
        canonicalize_name(name): set(extras)
        for name, extras in contract.get("active_distribution_extras", {}).items()
    }
    installed: dict[str, Version] = {}
    for dist in metadata.distributions():
        name = canonicalize_name(dist.metadata.get("Name") or "")
        if name:
            try:
                installed[name] = Version(dist.version)
            except Exception as exc:
                errors.append(f"{name}: unreadable installed version {dist.version!r}: {exc}")

    for name, requirements in declarations().items():
        found = installed.get(name)
        if found is None:
            errors.append(f"{name}: declared by Hub but absent from image")
            continue
        for req in requirements:
            if req.specifier and not req.specifier.contains(found, prereleases=True):
                errors.append(f"{name}=={found} does not satisfy Hub declaration {req}")

    # Relationship gate: requirements come from the versions actually installed,
    # not from whichever versions happen to be present in a developer venv.
    for dist in metadata.distributions():
        holder = canonicalize_name(dist.metadata.get("Name") or "")
        if not sibling(holder):
            continue
        for raw in dist.requires or []:
            req = Requirement(raw)
            if not requirement_applies(req, active_extras.get(holder, set())):
                continue
            target = canonicalize_name(req.name)
            found = installed.get(target)
            if found is None:
                errors.append(f"{holder}=={dist.version} requires {req}, but {target} is absent")
            elif req.specifier and not req.specifier.contains(found, prereleases=True):
                errors.append(f"{holder}=={dist.version} requires {req}, found {target}=={found}")

    probes = contract.get("extra_import_probes", [])
    if not probes:
        errors.append("import contract contains zero probes")
    for probe in probes:
        label = probe["module"] + "".join(f".{attr}" for attr in probe.get("attrs", []))
        try:
            obj = importlib.import_module(probe["module"])
            for attr in probe.get("attrs", []):
                obj = getattr(obj, attr)
        except Exception as exc:
            errors.append(f"import contract {label} failed: {type(exc).__name__}: {exc}")
    errors.extend(runtime_immutability_errors())
    return errors


if __name__ == "__main__":
    failures = verify()
    if failures:
        print("PRODUCTION IMAGE DEPENDENCY CONTRACT FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Production image dependency contract verified")
