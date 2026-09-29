"""Static leaf-package discovery for the ``scitex-hub dev`` facade."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

CAPABILITY_ENTRYPOINT_GROUP = "scitex_hub.dev"


@dataclass(frozen=True)
class LeafSpec:
    distribution: str
    module: str
    executable: str
    capability: str
    domain: str


LEAF_SPECS: tuple[LeafSpec, ...] = (
    LeafSpec(
        "scitex-storage",
        "scitex_storage",
        "scitex-storage",
        "validate_storage_contract",
        "storage",
    ),
    LeafSpec(
        "scitex-resource",
        "scitex_resource",
        "scitex-resource",
        "collect_host_context",
        "resource",
    ),
    LeafSpec(
        "scitex-hpc",
        "scitex_hpc",
        "scitex-hpc",
        "validate_customer_policy",
        "slurm",
    ),
    LeafSpec(
        "scitex-ssh",
        "scitex_ssh",
        "scitex-ssh",
        "validate_customer_policy",
        "ssh",
    ),
    LeafSpec(
        "scitex-container",
        "scitex_container",
        "scitex-container",
        "validate_runtime_projection",
        "container",
    ),
)


def _check(name: str, ok: bool, observed: Any, expected: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "observed": observed,
        "expected": expected,
    }


def _normalise_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _valid_console_entrypoint(value: str | None, module: str) -> bool:
    if not value:
        return False
    module_ref, separator, callable_ref = value.partition(":")
    if not separator or not callable_ref:
        return False
    if not all(part.isidentifier() for part in module_ref.split(".")):
        return False
    if module_ref != module and not module_ref.startswith(f"{module}."):
        return False
    return all(part.isidentifier() for part in callable_ref.split("."))


def build_dependency_report(
    *,
    distribution: str,
    module: str,
    executable: str,
    capability: str,
    domain: str,
    version: str | None,
    package_owners: list[str],
    module_file_owned: bool,
    console_entrypoint_value: str | None,
    capability_entrypoint_value: str | None,
    runtime_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed verdict without importing leaf package code."""
    expected_owner = _normalise_dist(distribution)
    normalised_owners = sorted(
        {_normalise_dist(name) for name in package_owners}
    )
    expected_capability = f"{module}:{capability}"
    preflight_checks = [
        _check("distribution", version is not None, version, "installed distribution"),
        _check(
            "module_distribution",
            normalised_owners == [expected_owner],
            normalised_owners,
            f"{module} owned only by {distribution}",
        ),
        _check(
            "module_file",
            module_file_owned,
            module_file_owned,
            "package __init__.py is listed by the selected distribution",
        ),
        _check(
            "console_entrypoint",
            _valid_console_entrypoint(console_entrypoint_value, module),
            console_entrypoint_value,
            f"valid {module}:callable console entry point",
        ),
        _check(
            "typed_capability_entrypoint",
            capability_entrypoint_value == expected_capability,
            capability_entrypoint_value,
            (
                f"[{CAPABILITY_ENTRYPOINT_GROUP}] {domain} = "
                f"{expected_capability}"
            ),
        ),
    ]
    preflight_ready = all(item["ok"] for item in preflight_checks)
    runtime_ok = bool(runtime_validation and runtime_validation.get("ready") is True)
    checks = [
        *preflight_checks,
        _check(
            "runtime_validation",
            runtime_ok,
            runtime_validation,
            "owner capability executed and returned a structured ready verdict",
        ),
    ]
    ready = all(item["ok"] for item in checks)
    return {
        "distribution": distribution,
        "module": module,
        "executable": executable,
        "capability": capability,
        "installed": version is not None,
        "version": version,
        "preflight_ready": preflight_ready,
        "ready": ready,
        "checks": checks,
        "remedy": (
            None
            if ready
            else (
                f"install/refresh {distribution} and run its typed "
                "validation adapter in the active managed uv environment"
            )
        ),
    }


def _entrypoint_value(
    dist: metadata.Distribution, group: str, name: str
) -> str | None:
    matches = [
        entry.value
        for entry in dist.entry_points
        if entry.group == group and entry.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _editable_module_file_owned(
    dist: metadata.Distribution, module: str
) -> bool:
    """Verify a PEP 610 editable source tree without importing its code."""
    try:
        direct_url = json.loads(dist.read_text("direct_url.json") or "")
        if not isinstance(direct_url, dict):
            return False
        direct_url_value = direct_url.get("url")
        dir_info = direct_url.get("dir_info")
        if not isinstance(direct_url_value, str) or not isinstance(dir_info, dict):
            return False
        if dir_info.get("editable") is not True:
            return False
        parsed = urlparse(direct_url_value)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            return False
        decoded_path = Path(url2pathname(parsed.path))
        if not decoded_path.is_absolute():
            return False
        root = decoded_path.resolve(strict=True)
        project_data = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
        project_name = project_data["project"]["name"]
        distribution_name = dist.metadata["Name"]
    except (
        AttributeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return False
    if not isinstance(project_name, str) or not isinstance(distribution_name, str):
        return False
    if _normalise_dist(project_name) != _normalise_dist(distribution_name):
        return False

    relative = Path(*module.split(".")) / "__init__.py"
    candidates = ((root / "src", root / "src" / relative), (root, root / relative))
    for source_root, candidate in candidates:
        if not _editable_pth_maps_root(dist, source_root):
            continue
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            continue
        if resolved == candidate and resolved.is_file():
            return True
    return False


def _editable_pth_maps_root(
    dist: metadata.Distribution, expected_root: Path
) -> bool:
    """Prove the installed editable adds ``expected_root`` to sys.path."""
    try:
        install_root = Path(str(dist.locate_file(""))).resolve(strict=True)
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    for item in dist.files or ():
        relative = Path(str(item))
        if (
            relative.is_absolute()
            or relative.parent != Path(".")
            or relative.suffix != ".pth"
        ):
            continue
        try:
            pth = Path(str(dist.locate_file(item)))
            if pth.parent.resolve(strict=True) != install_root:
                continue
            lines = pth.read_text(encoding="utf-8").splitlines()
        except (AttributeError, OSError, TypeError, ValueError):
            continue
        for raw_line in lines:
            # Match site.addpackage(): path lines keep leading whitespace;
            # only trailing whitespace is removed before resolution.
            line = raw_line.rstrip()
            if (
                not line
                or line.startswith("#")
                or line.startswith(("import ", "import\t"))
            ):
                continue
            mapped = Path(line)
            if not mapped.is_absolute():
                mapped = pth.parent / mapped
            try:
                mapped = mapped.resolve(strict=True)
            except OSError:
                continue
            if mapped == expected_root:
                return True
    return False


def _module_file_owned(dist: metadata.Distribution, module: str) -> bool:
    relative = Path(*module.split(".")) / "__init__.py"
    files = {Path(str(item)) for item in (dist.files or ())}
    if relative not in files:
        return _editable_module_file_owned(dist, module)
    source = Path(str(dist.locate_file(relative))).resolve()
    distribution_root = Path(str(dist.locate_file(""))).resolve()
    try:
        source.relative_to(distribution_root)
    except ValueError:
        return False
    return source.is_file()


def inspect_leaf(spec: LeafSpec) -> dict[str, Any]:
    """Inspect package ownership and typed contract metadata without imports."""
    try:
        dist = metadata.distribution(spec.distribution)
        version = dist.version
        console_entrypoint = _entrypoint_value(
            dist, "console_scripts", spec.executable
        )
        capability_entrypoint = _entrypoint_value(
            dist, CAPABILITY_ENTRYPOINT_GROUP, spec.domain
        )
        module_owned = _module_file_owned(dist, spec.module)
    except metadata.PackageNotFoundError:
        dist = None
        version = None
        console_entrypoint = None
        capability_entrypoint = None
        module_owned = False

    package_owners = list(
        metadata.packages_distributions().get(spec.module.split(".")[0], [])
    )
    if not package_owners and module_owned and dist is not None:
        package_owners = [dist.metadata.get("Name", spec.distribution)]
    return build_dependency_report(
        distribution=spec.distribution,
        module=spec.module,
        executable=spec.executable,
        capability=spec.capability,
        domain=spec.domain,
        version=version,
        package_owners=package_owners,
        module_file_owned=module_owned,
        console_entrypoint_value=console_entrypoint,
        capability_entrypoint_value=capability_entrypoint,
        runtime_validation=None,
    )


def collect_dev_doctor() -> dict[str, Any]:
    packages = {spec.distribution: inspect_leaf(spec) for spec in LEAF_SPECS}
    checks = [
        _check(name, report["ready"], report, f"{name} typed capability ready")
        for name, report in packages.items()
    ]
    return {
        "schema_version": 1,
        "operation": "dev.doctor",
        "mutating": False,
        "ready": all(item["ok"] for item in checks),
        "checks": checks,
        "packages": packages,
    }


def collect_leaf_capability(distribution: str) -> dict[str, Any]:
    specs = {spec.distribution: spec for spec in LEAF_SPECS}
    spec = specs[distribution]
    package = inspect_leaf(spec)
    return {
        "schema_version": 1,
        "operation": f"dev.{spec.domain}.validate",
        "mutating": False,
        "ready": package["ready"],
        "delegate": distribution,
        "checks": package["checks"],
        "package": package,
    }
