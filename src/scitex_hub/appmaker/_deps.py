"""App dependency checking and installation.

Reads ``dependencies`` from manifest.json and checks whether they are satisfied.
Supports: python (pip), system (apt/dpkg), node (npm), r (R packages).

Designed to run both inside Apptainer containers and on the host.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def check_deps(manifest: dict[str, Any]) -> dict[str, list[str]]:
    """Check which dependencies from a manifest are missing.

    Args:
        manifest: Parsed manifest.json dict (must have ``dependencies`` key).

    Returns:
        Dict mapping dep type → list of missing dependency specs.
        Empty dict means all dependencies are satisfied.
    """
    deps = manifest.get("dependencies") or {}
    missing: dict[str, list[str]] = {}

    for dep_type, specs in deps.items():
        if not specs:
            continue
        checker = _CHECKERS.get(dep_type)
        if checker is None:
            logger.debug("[deps] no checker for dep type: %s", dep_type)
            continue
        missing_specs = checker(specs)
        if missing_specs:
            missing[dep_type] = missing_specs

    return missing


def check_deps_from_manifest(manifest_path: Path) -> dict[str, list[str]]:
    """Convenience: load manifest.json then check deps."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return check_deps(data)


def install_deps(
    manifest: dict[str, Any],
    dep_type: str,
    *,
    timeout: int = 300,
) -> dict[str, Any]:
    """Install dependencies of a specific type from a manifest.

    Args:
        manifest: Parsed manifest.json dict.
        dep_type: One of "python", "system", "node", "r".
        timeout: Max seconds for the install command.

    Returns:
        Dict with ``success``, ``installed``, ``error`` keys.
    """
    deps = manifest.get("dependencies") or {}
    specs = deps.get(dep_type, [])
    if not specs:
        return {"success": True, "installed": [], "error": ""}

    installer = _INSTALLERS.get(dep_type)
    if installer is None:
        return {
            "success": False,
            "installed": [],
            "error": f"No installer for: {dep_type}",
        }

    return installer(specs, timeout=timeout)


def format_missing_report(missing: dict[str, list[str]]) -> str:
    """Format missing dependencies as a human-readable string."""
    if not missing:
        return "All dependencies satisfied."
    lines = []
    for dep_type, specs in missing.items():
        label = _TYPE_LABELS.get(dep_type, dep_type)
        lines.append(f"{label}: {', '.join(specs)}")
    return "Missing dependencies:\n" + "\n".join(f"  - {line}" for line in lines)


# --- Checkers ---


def _check_python(specs: list[str]) -> list[str]:
    """Check which Python packages are missing using importlib.metadata."""
    import importlib.metadata

    missing = []
    for spec in specs:
        # Extract package name from spec like "numpy>=1.24"
        name = _parse_pkg_name(spec)
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(spec)
    return missing


def _check_system(specs: list[str]) -> list[str]:
    """Check which system packages are missing using dpkg-query."""
    if not shutil.which("dpkg-query"):
        logger.debug("[deps] dpkg-query not found — skipping system dep check")
        return []
    missing = []
    for pkg in specs:
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f", "${Status}", pkg],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "install ok installed" not in result.stdout:
                missing.append(pkg)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(pkg)
    return missing


def _check_node(specs: list[str]) -> list[str]:
    """Check which Node.js packages are missing."""
    npm = shutil.which("npm")
    if not npm:
        logger.debug("[deps] npm not found — skipping node dep check")
        return specs if specs else []
    missing = []
    for spec in specs:
        name = _parse_pkg_name(spec)
        try:
            result = subprocess.run(
                ["npm", "list", name, "--depth=0"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                missing.append(spec)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(spec)
    return missing


def _check_r(specs: list[str]) -> list[str]:
    """Check which R packages are missing."""
    rscript = shutil.which("Rscript")
    if not rscript:
        logger.debug("[deps] Rscript not found — skipping R dep check")
        return specs if specs else []
    missing = []
    for pkg in specs:
        try:
            result = subprocess.run(
                [
                    "Rscript",
                    "-e",
                    f'if (!require("{pkg}", quietly=TRUE)) quit(status=1)',
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                missing.append(pkg)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(pkg)
    return missing


# --- Installers ---


def _install_python(specs: list[str], *, timeout: int = 300) -> dict[str, Any]:
    """Install Python packages via pip."""
    try:
        result = subprocess.run(
            ["pip", "install", "--no-input", *specs],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"success": True, "installed": specs, "error": ""}
        return {"success": False, "installed": [], "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "installed": [],
            "error": f"Timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {"success": False, "installed": [], "error": "pip not found"}


def _install_system(specs: list[str], *, timeout: int = 300) -> dict[str, Any]:
    """Install system packages via apt-get."""
    try:
        result = subprocess.run(
            ["apt-get", "install", "-y", *specs],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"success": True, "installed": specs, "error": ""}
        return {"success": False, "installed": [], "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "installed": [],
            "error": f"Timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {"success": False, "installed": [], "error": "apt-get not found"}


def _install_node(specs: list[str], *, timeout: int = 300) -> dict[str, Any]:
    """Install Node.js packages via npm."""
    try:
        result = subprocess.run(
            ["npm", "install", *specs],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"success": True, "installed": specs, "error": ""}
        return {"success": False, "installed": [], "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "installed": [],
            "error": f"Timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {"success": False, "installed": [], "error": "npm not found"}


def _install_r(specs: list[str], *, timeout: int = 300) -> dict[str, Any]:
    """Install R packages via install.packages()."""
    pkgs_str = ", ".join(f'"{p}"' for p in specs)
    r_cmd = f'install.packages(c({pkgs_str}), repos="https://cran.r-project.org")'
    try:
        result = subprocess.run(
            ["Rscript", "-e", r_cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"success": True, "installed": specs, "error": ""}
        return {"success": False, "installed": [], "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "installed": [],
            "error": f"Timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {"success": False, "installed": [], "error": "Rscript not found"}


# --- Helpers ---


def _parse_pkg_name(spec: str) -> str:
    """Extract package name from a version spec like 'numpy>=1.24' or 'react>=18'."""
    for sep in (">=", "<=", "==", "!=", ">", "<", "~="):
        if sep in spec:
            return spec.split(sep, 1)[0].strip()
    return spec.strip()


# --- Container building ---


def build_container(
    app_dir: Path,
    *,
    output_dir: Optional[Path] = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Build an Apptainer container from a .def file in an app directory.

    Looks for ``container`` field in manifest.json. If it's a .def file,
    builds it into a .sif file.

    Args:
        app_dir: Path to the app directory containing manifest.json.
        output_dir: Where to place the .sif file. Defaults to app_dir.
        timeout: Max build time in seconds.

    Returns:
        Dict with ``success``, ``sif_path``, ``error`` keys.
    """
    manifest_path = app_dir / "manifest.json"
    if not manifest_path.is_file():
        return {"success": False, "sif_path": "", "error": "No manifest.json found"}

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    container = data.get("container")
    if not container:
        return {
            "success": False,
            "sif_path": "",
            "error": "No container field in manifest",
        }

    container_str = str(container)

    # If already a .sif, nothing to build
    if container_str.endswith(".sif"):
        sif_path = app_dir / container_str
        if sif_path.is_file():
            return {"success": True, "sif_path": str(sif_path), "error": ""}
        return {
            "success": False,
            "sif_path": "",
            "error": f"SIF file not found: {sif_path}",
        }

    # Build from .def
    if not container_str.endswith(".def"):
        return {
            "success": False,
            "sif_path": "",
            "error": f"Container must be a .def or .sif file, got: {container_str}",
        }

    def_path = app_dir / container_str
    if not def_path.is_file():
        return {
            "success": False,
            "sif_path": "",
            "error": f"Def file not found: {def_path}",
        }

    if not shutil.which("apptainer"):
        return {
            "success": False,
            "sif_path": "",
            "error": "apptainer not found on PATH",
        }

    out = output_dir or app_dir
    out.mkdir(parents=True, exist_ok=True)
    sif_name = def_path.stem + ".sif"
    sif_path = out / sif_name

    logger.info("[deps] Building container: %s → %s", def_path, sif_path)

    try:
        result = subprocess.run(
            ["apptainer", "build", "--fakeroot", str(sif_path), str(def_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"success": True, "sif_path": str(sif_path), "error": ""}
        return {"success": False, "sif_path": "", "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "sif_path": "",
            "error": f"Build timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {"success": False, "sif_path": "", "error": "apptainer not found"}


# --- Registry ---

_CHECKERS = {
    "python": _check_python,
    "system": _check_system,
    "node": _check_node,
    "r": _check_r,
}

_INSTALLERS = {
    "python": _install_python,
    "system": _install_system,
    "node": _install_node,
    "r": _install_r,
}

_TYPE_LABELS = {
    "python": "Python (pip)",
    "system": "System (apt)",
    "node": "Node.js (npm)",
    "r": "R (CRAN)",
    "other": "Other",
}


# EOF
