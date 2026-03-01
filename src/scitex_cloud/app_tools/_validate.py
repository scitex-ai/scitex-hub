"""App validator — check structure, security, and manifest compliance."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

REQUIRED_FILES = [
    "apps.py",
    "views.py",
    "urls.py",
    "LICENSE",
    "README.md",
    "manifest.json",
]

FORBIDDEN_PATTERNS = [
    (r"\bsubprocess\b", "subprocess"),
    (r"\bos\.system\b", "os.system"),
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\b__import__\b", "__import__"),
]

MANIFEST_REQUIRED_KEYS = ["name", "label", "version", "icon"]


def validate(app_dir: str | Path) -> list[str]:
    """Run all validations on a local app directory.

    Returns list of error strings (empty = valid).
    """
    errors = []
    errors.extend(validate_structure(app_dir))
    errors.extend(validate_security(app_dir))
    errors.extend(validate_manifest(app_dir))
    return errors


def validate_structure(app_dir: str | Path) -> list[str]:
    """Check that required files exist."""
    errors = []
    root = Path(app_dir)

    if not root.exists():
        return [f"App directory does not exist: {root}"]

    for required in REQUIRED_FILES:
        if not (root / required).exists():
            errors.append(f"Missing required file: {required}")

    # Check template pattern (derive app_name from directory or manifest)
    app_name = _get_app_name(root)
    if app_name:
        partial = root / "templates" / app_name / "index_partial.html"
        if not partial.exists():
            errors.append(f"Missing template: templates/{app_name}/index_partial.html")

    # Check agents config
    agents_paths = [root / ".agents" / "agents.json", root / ".agents" / "README.md"]
    if not any(p.exists() for p in agents_paths):
        errors.append("Missing agents config: .agents/agents.json or .agents/README.md")

    return errors


def validate_security(app_dir: str | Path) -> list[str]:
    """Scan Python files for forbidden patterns."""
    errors = []
    root = Path(app_dir)

    for py_file in root.rglob("*.py"):
        # Skip __pycache__ and .git
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relpath = py_file.relative_to(root)
        for pattern, name in FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                errors.append(f"Forbidden pattern '{name}' found in {relpath}")

    return errors


def validate_manifest(app_dir: str | Path) -> list[str]:
    """Check manifest.json schema and content."""
    errors = []
    root = Path(app_dir)
    manifest_path = root / "manifest.json"

    if not manifest_path.exists():
        return ["manifest.json not found"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"manifest.json is not valid JSON: {e}"]

    if not isinstance(data, dict):
        return ["manifest.json must be a JSON object"]

    for key in MANIFEST_REQUIRED_KEYS:
        if key not in data:
            errors.append(f"manifest.json missing required key: '{key}'")

    # Validate name matches directory convention
    name = data.get("name", "")
    if name and not name.endswith("_app"):
        errors.append(f"manifest.json 'name' should end with '_app' (got: '{name}')")

    # Validate version format
    version = data.get("version", "")
    if version and not re.match(r"^\d+\.\d+\.\d+", version):
        errors.append(f"manifest.json 'version' should be semver (got: '{version}')")

    return errors


def _get_app_name(root: Path) -> str:
    """Derive app name from manifest or directory name."""
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data.get("name", "")
        except (json.JSONDecodeError, OSError):
            pass
    return root.name


# EOF
