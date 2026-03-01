"""App launcher — local development server for app plugins."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def dev_server(app_dir: str | Path, port: int = 8000) -> None:
    """Start or print instructions for local app development.

    For now, prints instructions on how to test the app within the
    full SciTeX workspace. A standalone lightweight server may be
    added in a future version.

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
        print(f"Error: {root} does not look like a SciTeX app (missing apps.py).")
        print("Run 'scitex-cloud app init' first to scaffold the boilerplate.")
        sys.exit(1)

    print(f"  App: {app_name}")
    print(f"  Dir: {root}")
    print(f"  Port: {port}")
    print()
    print("  To test your app in the SciTeX workspace:")
    print()
    print("  1. Symlink into apps/:")
    print(f"     ln -s {root} apps/{app_name}")
    print()
    print("  2. Register in workspace registry:")
    print(f"     Add ModuleConfig(name='{app_name}', ...) to")
    print("     apps/workspace_app/registry.py")
    print()
    print("  3. Add to INSTALLED_APPS in settings:")
    print(f"     'apps.{app_name}',")
    print()
    print("  4. Restart the dev server:")
    print("     make env=dev restart")
    print()
    print(f"  5. Open http://127.0.0.1:{port} and switch to your module tab")
    print()
    print("  Tip: Run 'scitex-cloud app validate .' to check your app is complete.")


# EOF
