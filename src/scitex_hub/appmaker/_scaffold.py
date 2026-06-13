"""App initializer — generate complete boilerplate for a SciTeX app plugin."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ._license import generate_license_text
from ._scaffold_agent_context import _agents_md
from ._scaffold_html import (
    _agents_json,
    _app_css,
    _apps_py,
    _index_html,
    _index_partial_html,
    _manifest_json,
    _readme_md,
    _skill_py,
    _tests_py,
    _urls_py,
    _views_py,
)
from ._scaffold_react import build_react_files

logger = logging.getLogger(__name__)


def init_app(
    target_dir: str | Path,
    name: str,
    *,
    label: str = "",
    icon: str = "fas fa-puzzle-piece",
    description: str = "",
    manifest: Optional[dict] = None,
    license_id: str = "AGPL-3.0",
    overwrite: bool = False,
    frontend_type: str = "html",
) -> list[str]:
    """Generate complete app boilerplate in target_dir.

    Parameters
    ----------
    target_dir : path
        Project directory (e.g. data/users/alice/proj/my_app/).
    name : str
        Python module name (must end with _app, e.g. 'my_awesome_app').
    label : str
        Human-readable label (default: derived from name).
    icon : str
        Font Awesome icon class (default: 'fas fa-puzzle-piece').
    description : str
        Short description for the app.
    manifest : dict, optional
        Extra manifest fields to merge.
    license_id : str
        SPDX license identifier (default: 'AGPL-3.0').
    overwrite : bool
        If True, overwrite existing files (default: False).
    frontend_type : str
        Frontend type: 'html' (default) or 'react' for React+Vite+Zustand.

    Returns
    -------
    list[str]
        Relative paths of created files.
    """
    target = Path(target_dir)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    if not label:
        label = name.replace("_", " ").title().removesuffix(" App")

    class_name = label.replace(" ", "") + "App"
    files = _build_all_files(
        name,
        label,
        class_name,
        icon,
        description,
        manifest,
        license_id,
        frontend_type=frontend_type,
    )

    created = []
    for relpath, content in files.items():
        filepath = target / relpath
        if filepath.exists() and not overwrite:
            logger.debug("Skipping existing file: %s", relpath)
            continue
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        created.append(relpath)
        logger.debug("Created: %s", relpath)

    logger.info("Scaffolded %d/%d files in %s", len(created), len(files), target)
    return created


def _build_all_files(
    name,
    label,
    class_name,
    icon,
    description,
    manifest,
    license_id,
    *,
    frontend_type: str = "html",
):
    """Build dict of relpath -> content for all scaffold files.

    LAYOUT (M4 done-gate, lead msg 711b5d90 + a2b21da8):

    Wrapper-root files (build config + project metadata that the
    operator and downstream tooling read directly):

      <wrapper>/pyproject.toml
      <wrapper>/README.md
      <wrapper>/LICENSE
      <wrapper>/AGENTS.md
      <wrapper>/.gitignore

    Python-package files (nested under ``<name>/`` so pip + hatchling
    can build the wheel — the package directory MUST match the
    normalized project name, otherwise ``hatchling.build`` errors with
    "Unable to determine which files to ship inside the wheel"):

      <wrapper>/<name>/__init__.py
      <wrapper>/<name>/apps.py
      <wrapper>/<name>/views.py
      <wrapper>/<name>/urls.py
      <wrapper>/<name>/tests.py
      <wrapper>/<name>/skill.py
      <wrapper>/<name>/manifest.json
      <wrapper>/<name>/templates/<name>/...
      <wrapper>/<name>/static/<name>/...
      <wrapper>/<name>/.agents/agents.json
      <wrapper>/<name>/docs/PLATFORM.md

    The hub's ``pip_install_user_app`` runs ``pip install --no-deps
    --target=<install_dir> <gitea-archive-url>`` against this shape;
    hatchling auto-detects ``<name>/`` as the package directory (via
    the ``[tool.hatch.build.targets.wheel] packages = ["<name>"]``
    declaration in the emitted pyproject) and lands the wheel cleanly
    on ``sys.path``.
    """
    use_react = frontend_type == "react"
    files = {}

    # -----------------------------------------------------------------
    # Wrapper-root files (build system + project metadata)
    # -----------------------------------------------------------------

    files["pyproject.toml"] = _pyproject_toml(name, label, description, license_id)
    files["README.md"] = _readme_md(
        name, label, description, license_id, frontend_type=frontend_type
    )

    license_text = generate_license_text(license_id)
    if license_text is None:
        license_text = generate_license_text("AGPL-3.0")
    files["LICENSE"] = license_text

    files["AGENTS.md"] = _agents_md(name, label, icon, description)

    files[".gitignore"] = "\n".join(
        [
            "# Runtime data (created by platform, not app source)",
            "scitex/",
            "",
            "# Python",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.egg-info/",
            "",
            "# Environment",
            ".env",
            ".env.*",
            ".venv/",
            "venv/",
            "node_modules/",
            "",
            "# IDE",
            ".vscode/",
            ".idea/",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
            "",
        ]
    )

    # -----------------------------------------------------------------
    # Python-package files (nested under <name>/)
    # -----------------------------------------------------------------

    files[f"{name}/__init__.py"] = f'"""SciTeX Hub App: {label}."""\n'
    files[f"{name}/apps.py"] = _apps_py(name, label, class_name)
    files[f"{name}/views.py"] = _views_py(name, label, description)
    files[f"{name}/urls.py"] = _urls_py(name)
    files[f"{name}/tests.py"] = _tests_py(name, label)
    files[f"{name}/skill.py"] = _skill_py(name, label, description)
    files[f"{name}/manifest.json"] = _manifest_json(
        name, label, icon, description, manifest, license_id, frontend_type
    )
    files[f"{name}/templates/{name}/index.html"] = _index_html(
        name, label, include_js_bundle=use_react
    )
    files[f"{name}/templates/{name}/index_partial.html"] = _index_partial_html(
        name, label, icon, react_mount=use_react
    )
    files[f"{name}/static/{name}/css/{name}.css"] = _app_css(name, label)
    files[f"{name}/.agents/agents.json"] = _agents_json(name, label)

    from ._scaffold_docs import _platform_docs_md

    files[f"{name}/docs/PLATFORM.md"] = _platform_docs_md(name)

    # React frontend files (mount under the package directory too)
    if use_react:
        for relpath, content in build_react_files(name, label, icon).items():
            files[f"{name}/{relpath}"] = content

    return files


def _pyproject_toml(name, label, description, license_id):
    """Generate pyproject.toml for dual-mode app (standalone + scitex-hub extension).

    Includes ``[tool.hatch.build.targets.wheel] packages = ["<name>"]``
    so the wheel build works against the nested-package layout that
    ``_build_all_files`` emits — without this, hatchling errors
    "Unable to determine which files to ship inside the wheel using
    the following heuristics" and ``pip_install_user_app`` fails at
    install time.
    """
    slug = name.replace("_", "-")
    desc = description or f"{label} — a SciTeX Hub app."
    return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{slug}"
version = "0.1.0"
description = "{desc}"
requires-python = ">=3.10"
license = "{license_id}"

[project.scripts]
{slug} = "{name}._cli:main"

[project.optional-dependencies]
scitex = ["scitex-app>=0.1.0", "scitex-ui>=0.1.0"]
dev = ["pytest>=7.0.0"]

[project.entry-points."scitex_modules"]
{name} = "{name}:get_module_config"

[tool.hatch.build.targets.wheel]
packages = ["{name}"]
"""


# EOF
