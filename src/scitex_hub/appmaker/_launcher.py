"""App launcher — local development setup for SciTeX Hub app plugins."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import scitex_logging as slogging

logger = slogging.getLogger(__name__)
# PS-220: the dev-server walkthrough is CLI stdout, not diagnostics, so it
# keeps stdout (getLogger writes to stderr) and gains the SciTeX level.
console = slogging.getConsole(__name__)


def dev_server(app_dir: str | Path, port: int = 8000) -> None:
    """Set up a local app for development in the SciTeX workspace.

    Validates the app, creates a symlink into apps/ if needed,
    and reports remaining manual steps.

    Parameters
    ----------
    app_dir : path
        Path to the app plugin directory.
    port : int
        Port number for the dev server (default: 8000).
    """
    root = Path(app_dir).resolve()
    app_name = root.name

    # Check basic structure
    if not (root / "apps.py").exists():
        console.error(f"Error: {root} does not look like a SciTeX Hub app (missing apps.py).")
        console.error("Run 'scitex-hub app init' first to scaffold the boilerplate.")
        sys.exit(1)

    # Run validation
    from ._validate import validate

    errors = validate(str(root))
    if errors:
        console.error(f"  Validation found {len(errors)} issue(s):")
        for err in errors:
            console.error(f"    x {err}")
        console.info("")
        console.error("  Fix these issues before proceeding.")
        sys.exit(1)

    console.info(f"  App:  {app_name}")
    console.info(f"  Dir:  {root}")
    console.info(f"  Port: {port}")
    console.success("  Validation: PASSED")
    console.info("")

    # Try to create symlink
    project_root = _find_project_root()
    if project_root:
        apps_dir = project_root / "apps"
        symlink_target = apps_dir / app_name
        if symlink_target.exists():
            if symlink_target.is_symlink():
                console.info(f"  Symlink exists: apps/{app_name} -> {root}")
            else:
                console.warning(f"  apps/{app_name} already exists (not a symlink)")
        else:
            try:
                symlink_target.symlink_to(root)
                console.success(f"  Created symlink: apps/{app_name} -> {root}")
            except OSError as exc:
                console.warning(f"  Could not create symlink: {exc}")
                console.warning(f"  Run manually: ln -s {root} {symlink_target}")
        console.info("")

    # Print remaining steps
    console.info("  Next steps:")
    console.info("")
    console.info("  1. Push your app to a Gitea repository")
    console.info("")
    console.info("  2. Dev Install from the workspace:")
    console.info("     Hub → Explore → click 'Dev Install' on your repo")
    console.info("     Your app appears as a workspace tab immediately.")
    console.info("")
    console.info(f"  3. Open http://127.0.0.1:{port} and switch to your app tab")
    console.info("")
    console.info("  Tip: Run 'scitex-hub app validate .' to check your app.")
    console.info("")
    console.info("  Note: Do NOT edit registry.py or INSTALLED_APPS —")
    console.info("  those are for platform-builtin modules only.")


def _find_project_root() -> Path | None:
    """Walk up from cwd to find the scitex-hub project root."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "manage.py").exists() and (parent / "apps").exists():
            return parent
    # Check SCITEX_HUB_ROOT env var
    env_root = os.environ.get("SCITEX_HUB_ROOT")
    if env_root:
        root = Path(env_root)
        if root.exists():
            return root
    return None


# EOF
