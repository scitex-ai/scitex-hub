"""App launcher — local development setup for SciTeX Cloud app plugins."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def dev_server(app_dir: str | Path, port: int = 8000) -> None:
    """Set up a local app for development in the SciTeX workspace.

    Validates the app, creates a symlink into apps/ if needed,
    and prints remaining manual steps.

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
        print(f"Error: {root} does not look like a SciTeX Cloud app (missing apps.py).")
        print("Run 'scitex-cloud app init' first to scaffold the boilerplate.")
        sys.exit(1)

    # Run validation
    from ._validate import validate

    errors = validate(str(root))
    if errors:
        print(f"  Validation found {len(errors)} issue(s):")
        for err in errors:
            print(f"    x {err}")
        print()
        print("  Fix these issues before proceeding.")
        sys.exit(1)

    print(f"  App:  {app_name}")
    print(f"  Dir:  {root}")
    print(f"  Port: {port}")
    print("  Validation: PASSED")
    print()

    # Try to create symlink
    project_root = _find_project_root()
    if project_root:
        apps_dir = project_root / "apps"
        symlink_target = apps_dir / app_name
        if symlink_target.exists():
            if symlink_target.is_symlink():
                print(f"  Symlink exists: apps/{app_name} -> {root}")
            else:
                print(f"  apps/{app_name} already exists (not a symlink)")
        else:
            try:
                symlink_target.symlink_to(root)
                print(f"  Created symlink: apps/{app_name} -> {root}")
            except OSError as exc:
                print(f"  Could not create symlink: {exc}")
                print(f"  Run manually: ln -s {root} {symlink_target}")
        print()

    # Print remaining steps
    print("  Next steps:")
    print()
    print("  1. Push your app to a Gitea repository")
    print()
    print("  2. Dev Install from the workspace:")
    print("     Hub → Explore → click 'Dev Install' on your repo")
    print("     Your app appears as a workspace tab immediately.")
    print()
    print(f"  3. Open http://127.0.0.1:{port} and switch to your app tab")
    print()
    print("  Tip: Run 'scitex-cloud app validate .' to check your app.")
    print()
    print("  Note: Do NOT edit registry.py or INSTALLED_APPS —")
    print("  those are for platform-builtin modules only.")


def _find_project_root() -> Path | None:
    """Walk up from cwd to find the scitex-cloud project root."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "manage.py").exists() and (parent / "apps").exists():
            return parent
    # Check SCITEX_CLOUD_ROOT env var
    env_root = os.environ.get("SCITEX_CLOUD_ROOT")
    if env_root:
        root = Path(env_root)
        if root.exists():
            return root
    return None


# EOF
