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
import os
import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def dependency_resolution_provenance() -> str:
    """Return the deterministic resolution input embedded by the Dockerfile."""
    value = os.environ.get("SCITEX_HUB_DEPENDENCY_RESOLUTION", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise RuntimeError(
            "SCITEX_HUB_DEPENDENCY_RESOLUTION provenance is missing or invalid"
        )
    return value


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


def verify() -> list[str]:
    errors: list[str] = []
    try:
        dependency_resolution_provenance()
    except RuntimeError as exc:
        errors.append(str(exc))
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
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            target = canonicalize_name(req.name)
            found = installed.get(target)
            if found is None:
                errors.append(f"{holder}=={dist.version} requires {req}, but {target} is absent")
            elif req.specifier and not req.specifier.contains(found, prereleases=True):
                errors.append(f"{holder}=={dist.version} requires {req}, found {target}=={found}")

    contract = json.loads((ROOT / "scripts/deploy/preflight_contract.json").read_text())
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
    return errors


if __name__ == "__main__":
    try:
        provenance = dependency_resolution_provenance()
    except RuntimeError:
        provenance = "INVALID"
    print(f"Dependency resolution provenance: {provenance}")
    failures = verify()
    if failures:
        print("PRODUCTION IMAGE DEPENDENCY CONTRACT FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Production image dependency contract verified")
