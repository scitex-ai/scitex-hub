#!/usr/bin/env python
"""
Create admin user for SciTeX Hub platform.

Reads credentials from environment variables:
  SCITEX_HUB_ADMIN_USERNAME (required)
  SCITEX_HUB_ADMIN_EMAIL (required)
  SCITEX_HUB_ADMIN_PASSWORD (required)
  SCITEX_HUB_ADMIN_FIRST_NAME (optional)
  SCITEX_HUB_ADMIN_LAST_NAME (optional)
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault(
    "SCITEX_HUB_DJANGO_SETTINGS_MODULE", "config.settings.development"
)
django.setup()

from django.contrib.auth.models import User


def create_user():
    username = os.environ.get("SCITEX_HUB_ADMIN_USERNAME")
    email = os.environ.get("SCITEX_HUB_ADMIN_EMAIL")
    password = os.environ.get("SCITEX_HUB_ADMIN_PASSWORD")

    if not all([username, email, password]):
        print("Error: Required environment variables not set:")
        print("  SCITEX_HUB_ADMIN_USERNAME")
        print("  SCITEX_HUB_ADMIN_EMAIL")
        print("  SCITEX_HUB_ADMIN_PASSWORD")
        sys.exit(1)

    first_name = os.environ.get("SCITEX_HUB_ADMIN_FIRST_NAME", "")
    last_name = os.environ.get("SCITEX_HUB_ADMIN_LAST_NAME", "")

    try:
        if User.objects.filter(username=username).exists():
            print(f"User '{username}' already exists")
            user = User.objects.get(username=username)
            user.email = email
            user.save()
            print(f"Updated email for user '{username}' to '{email}'")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            print(f"Created user '{username}' with email '{email}'")
            print("Please change password after first login")

        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"User '{username}' now has admin privileges")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_user()
