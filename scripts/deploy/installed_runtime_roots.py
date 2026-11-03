#!/usr/bin/env python3
"""Resolve a retained capability closure, not every cached transitive package.

Docker's old anchor/C0 versions are cache bootstraps, not final version floors.
All installed SciTeX packages and their installed direct dependency capabilities
survive. Helpers referenced only by superseded third-party versions may leave
through normal compile/sync. Cached versions are preferences, never constraints.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

# Deliberate Docker end-user inputs plus Python packaging tools. SciTeX names
# are also discovered below; listing the direct inputs prevents a broken cache
# from silently removing a requested feature. C0/C1 cache versions are omitted.
EXPLICIT_RUNTIME_ROOTS = (
    "daphne",
    "psycopg2-binary",
    "figrecipe",
    "scitex-decorators",
    "scitex-sh",
    "scitex-io",
    "scitex-stats",
    "scitex-plt",
    "scitex-writer",
    "scitex-template",
    "scitex-linter",
    "scitex-ui",
    "openalex-local",
    "crossref-local",
    "pip",
    "setuptools",
    "wheel",
)


def project_name(name) -> str:
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name
    ):
        raise ValueError("Installed distribution has an invalid project name")
    return canonicalize_name(name)


def first_party(name: str) -> bool:
    return name == "figrecipe" or name == "scitex" or name.startswith("scitex-")


def installed_names(distributions=None) -> list[str]:
    """Validate metadata names independently of requirement generation."""
    distributions = metadata.distributions() if distributions is None else distributions
    names = {project_name(dist.metadata.get("Name", "")) for dist in distributions}
    if not names:
        raise ValueError("Installed runtime inventory is empty")
    return sorted(names - {"scitex-hub"})


def resolution_inputs(
    distributions=None, explicit_roots=EXPLICIT_RUNTIME_ROOTS, provenance=None
):
    """Return (capability requirements, cached-version preferences).

    Optional extras contribute a direct capability only if it is already
    installed and its marker applies on this platform for a declared extra.
    The owning package's active requirements remain enforced by the resolver.
    REQUESTED files are not used: installers can mark transitive packages too.
    """
    distributions = list(
        metadata.distributions() if distributions is None else distributions
    )
    installed_names(distributions)
    inventory = {}
    preferences = {}
    for dist in distributions:
        name = project_name(dist.metadata.get("Name", ""))
        version = str(Version(dist.version))
        if name in preferences and preferences[name] != version:
            raise ValueError("Ambiguous installed distribution versions")
        inventory[name] = dist
        preferences[name] = version
    roots = set(explicit_roots)
    reasons = {}
    for raw in roots:
        requirement = Requirement(raw)
        if requirement.url or requirement.marker:
            raise ValueError("Explicit runtime roots must be index requirements")
        reasons.setdefault(canonicalize_name(requirement.name), []).append(
            {"kind": "explicit Docker/runtime capability", "requirement": raw}
        )
    for name, dist in inventory.items():
        if not first_party(name):
            continue
        if name != "scitex-hub":
            roots.add(name)
            reasons.setdefault(name, []).append(
                {"kind": "installed first-party distribution"}
            )
        contexts = {"", *(dist.metadata.get_all("Provides-Extra") or [])}
        for raw in dist.requires or []:
            requirement = Requirement(raw)
            applies = requirement.marker is None or any(
                requirement.marker.evaluate({"extra": extra}) for extra in contexts
            )
            dependency = canonicalize_name(requirement.name)
            if applies and dependency in inventory and dependency != "scitex-hub":
                roots.add(dependency)
                reasons.setdefault(dependency, []).append(
                    {
                        "kind": "installed direct dependency",
                        "owner": name,
                        "requirement": raw,
                    }
                )
    if provenance is not None:
        provenance.update(
            {
                "baseline_versions": preferences,
                "root_reasons": reasons,
                "baseline_metadata": {
                    name: {
                        "version": preferences[name],
                        "requires_dist": dist.requires or [],
                        "provides_extra": dist.metadata.get_all("Provides-Extra") or [],
                    }
                    for name, dist in inventory.items()
                },
            }
        )
    return sorted(roots), [
        f"{name}=={version}" for name, version in sorted(preferences.items())
    ]


def write_inputs(
    roots_path,
    preferences_path,
    distributions=None,
    explicit_roots=EXPLICIT_RUNTIME_ROOTS,
    local_project=".[all]",
):
    manifest = {"schema": 1}
    roots, preferences = resolution_inputs(distributions, explicit_roots, manifest)
    if local_project:
        roots.append(local_project)
        manifest["root_reasons"]["scitex-hub"] = [
            {"kind": "local Hub source [all]", "requirement": local_project}
        ]
    roots_path, preferences_path = Path(roots_path), Path(preferences_path)
    roots_path.write_text("\n".join(roots) + "\n")
    seed = "\n".join(preferences) + "\n"
    preferences_path.write_text(seed)
    seed_path = preferences_path.with_suffix(".cached-preferences.in")
    seed_path.write_text(seed)
    helper = globals().get("__file__")
    manifest.update(
        {
            "roots": roots,
            "preference_input": preferences,
            "cached_preference_file": str(seed_path),
            "lock_file": str(preferences_path),
            "helper_sha256": hashlib.sha256(Path(helper).read_bytes()).hexdigest()
            if helper
            else None,
        }
    )
    roots_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return roots


def verify_closure(manifest_path, distributions=None):
    """Fail unless the installed closure retains all recorded capabilities."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["schema"] == 1
    distributions = metadata.distributions() if distributions is None else distributions
    after = {
        project_name(d.metadata.get("Name", "")): str(Version(d.version))
        for d in distributions
    }
    missing = set(manifest["root_reasons"]) - after.keys()
    if missing:
        raise ValueError(
            "Resolved closure lost retained capabilities: " + ", ".join(sorted(missing))
        )
    baseline = manifest["baseline_versions"]
    manifest["resolved_versions"] = after
    manifest["removed_cached_packages"] = sorted(baseline.keys() - after.keys())
    manifest["changed_versions"] = {
        name: [old, after[name]]
        for name, old in baseline.items()
        if name in after and old != after[name]
    }
    manifest["lock_sha256"] = hashlib.sha256(
        Path(manifest["lock_file"]).read_bytes()
    ).hexdigest()
    manifest["retained_capabilities_verified"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    if sys.argv[1] == "--verify-closure":
        manifest = verify_closure(sys.argv[2])
        print(f"Verified {len(manifest['root_reasons'])} retained runtime capabilities")
        return
    roots = write_inputs(sys.argv[1], sys.argv[2])
    print(
        f"Resolving {len(roots)} retained runtime capability roots; cached versions are preferences"
    )


if __name__ == "__main__":
    main()
