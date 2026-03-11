"""App validator — check structure, security, manifest, templates, and CSS."""

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

MANIFEST_REQUIRED_KEYS = ["name", "slug", "label", "version", "icon", "license"]

# Frame selectors that app CSS must not style
PROTECTED_SELECTORS = [
    ".workspace-sidebar",
    ".sidebar-title",
    ".panel-resizer",
    "footer",
]

# Forbidden frame block overrides
FORBIDDEN_BLOCK_OVERRIDES = [
    "workspace_worktree_pane",
    "workspace_ai_pane",
    "workspace_viewer_pane",
    "workspace_apps_pane",
]


def validate(app_dir: str | Path) -> list[str]:
    """Run all validations on a local app directory.

    Returns list of error strings (empty = valid).
    """
    errors = []
    errors.extend(validate_structure(app_dir))
    errors.extend(validate_security(app_dir))
    errors.extend(validate_manifest(app_dir))
    errors.extend(validate_templates(app_dir))
    errors.extend(validate_css(app_dir))
    errors.extend(validate_dependencies(app_dir))
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

    excluded_dirs = {"__pycache__", ".git", "scitex", "node_modules", ".venv", "venv"}
    for py_file in root.rglob("*.py"):
        if excluded_dirs & set(py_file.relative_to(root).parts):
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
    if name and not (name.endswith("_app") or name.endswith("-app")):
        errors.append(
            f"manifest.json 'name' should end with '_app' or '-app' (got: '{name}')"
        )

    # Validate version format
    version = data.get("version", "")
    if version and not re.match(r"^\d+\.\d+\.\d+", version):
        errors.append(f"manifest.json 'version' should be semver (got: '{version}')")

    return errors


def validate_templates(app_dir: str | Path) -> list[str]:
    """Check template compliance with workspace frame rules."""
    errors = []
    root = Path(app_dir)
    app_name = _get_app_name(root)
    if not app_name:
        return errors

    index_html = root / "templates" / app_name / "index.html"
    if not index_html.exists():
        return errors

    try:
        content = index_html.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return errors

    # Must extend global_base.html
    if "global_base.html" not in content:
        errors.append("index.html must extend 'global_base.html'")

    # Must have {% block content %}
    if "block content" not in content:
        errors.append("index.html must define {% block content %}")

    # Must NOT override frame blocks
    for block_name in FORBIDDEN_BLOCK_OVERRIDES:
        if f"block {block_name}" in content:
            errors.append(f"index.html must not override '{{% block {block_name} %}}'")

    return errors


def validate_css(app_dir: str | Path) -> list[str]:
    """Check CSS compliance with workspace frame rules."""
    errors = []
    root = Path(app_dir)

    for css_file in root.rglob("*.css"):
        if ".git" in str(css_file):
            continue
        try:
            content = css_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relpath = css_file.relative_to(root)

        # Warn about deprecated --color-* variables
        if re.search(r"var\(--color-", content):
            errors.append(
                f"{relpath}: use --workspace-* or --text-* CSS variables "
                f"instead of --color-* (see workspace template spec)"
            )

        # Check for !important on protected selectors
        for selector in PROTECTED_SELECTORS:
            pattern = re.escape(selector) + r"[^{]*\{[^}]*!important"
            if re.search(pattern, content, re.DOTALL):
                errors.append(f"{relpath}: must not use !important on '{selector}'")

        # Check for footer hiding
        if re.search(r"footer\s*\{[^}]*display\s*:\s*none", content, re.DOTALL):
            errors.append(f"{relpath}: must not hide the footer")

    return errors


def validate_dependencies(app_dir: str | Path) -> list[str]:
    """Check that manifest.json dependencies field is well-formed."""
    errors = []
    root = Path(app_dir)
    manifest_path = root / "manifest.json"

    if not manifest_path.exists():
        return errors

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return errors

    deps = data.get("dependencies")
    if deps is None:
        errors.append("manifest.json missing 'dependencies' field")
        return errors

    if not isinstance(deps, dict):
        errors.append("manifest.json 'dependencies' must be a JSON object")
        return errors

    valid_types = {"python", "system", "node", "r", "other"}
    for key, val in deps.items():
        if key not in valid_types:
            errors.append(f"manifest.json unknown dependency type: '{key}'")
        if not isinstance(val, list):
            errors.append(f"manifest.json dependencies.{key} must be a list")
        elif not all(isinstance(item, str) for item in val):
            errors.append(f"manifest.json dependencies.{key} items must be strings")

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
