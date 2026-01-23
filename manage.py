#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-20 19:32:25 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/manage.py


import os

"""Django's command-line utility for administrative tasks."""

import sys


def main():
    """Run administrative tasks. Prevent direct call of this file (manage.py) and guide to use docker."""

    print(f"Initial Args for manage.py: {sys.argv}")

    if (
        len(sys.argv) > 1
        and sys.argv[1] == "runserver"
        and ("from_docker" not in sys.argv)
    ):
        print("\n" + "=" * 70)
        print("❌ ERROR: Direct 'python manage.py runserver' is not allowed!")
        print("=" * 70)
        print(
            "\nPlease use docker (the Makefile) to ensure proper environment setup (e.g., Gitea):\n"
        )
        print("  For development:")
        print("    make ENV=dev start     # Start development environment")
        print("    make ENV=dev restart   # Restart development environment")
        print("    make ENV=dev reload    # Hot reload without reinstall\n")
        print("  For NAS deployment:")
        print("    make ENV=nas start     # Start NAS environment")
        print("    make ENV=nas restart   # Restart NAS environment\n")
        print("  Check status:")
        print("    make status            # Show active environment\n")
        print("=" * 70)
        print("The Makefile ensures:")
        print("  ✓ Only one environment runs at a time (exclusive mode)")
        print("  ✓ Proper environment variables are set")
        print("  ✓ All dependencies are correctly configured")
        print("  ✓ Docker containers are properly managed")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Add base and config directories to Python path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)  # Add base directory
    sys.path.insert(
        0, os.path.join(BASE_DIR, "config")
    )  # Add config directory
    # No need to add src directory anymore as it's been replaced by apps

    # Use new auto-detection settings module
    # Set SCITEX_CLOUD_ENV=nas for NAS deployment, defaults to development
    settings_module = os.environ.get(
        "SCITEX_CLOUD_DJANGO_SETTINGS_MODULE", "config.settings"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Drops from_docker argument if exists
    final_args = sys.argv.copy()
    if "from_docker" in final_args:
        final_args.remove("from_docker")
    print(f"Final Args for manage.py: {final_args}")

    execute_from_command_line(final_args)


if __name__ == "__main__":
    main()

# EOF
