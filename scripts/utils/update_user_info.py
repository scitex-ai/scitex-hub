#!/usr/bin/env python
"""
Update user information for SciTeX Hub platform.

Reads credentials from environment variables:
  SCITEX_HUB_ADMIN_USERNAME (required)
  SCITEX_HUB_ADMIN_EMAIL (required)
  SCITEX_HUB_ADMIN_PASSWORD (required)
  SCITEX_HUB_ADMIN_FIRST_NAME (optional)
  SCITEX_HUB_ADMIN_LAST_NAME (optional)
  SCITEX_HUB_ADMIN_AFFILIATION (optional)
"""

import os
import sys

import django

# Setup Django environment
os.environ.setdefault(
    "SCITEX_HUB_DJANGO_SETTINGS_MODULE", "config.settings.development"
)
django.setup()

from django.contrib.auth.models import User

from apps.infra.workspace_app.models import UserProfile


def update_user_info():
    """Update the user with information from environment variables"""
    username = os.environ.get("SCITEX_HUB_ADMIN_USERNAME")
    new_email = os.environ.get("SCITEX_HUB_ADMIN_EMAIL")
    new_password = os.environ.get("SCITEX_HUB_ADMIN_PASSWORD")

    if not all([username, new_email, new_password]):
        print("Error: Required environment variables not set:")
        print("  SCITEX_HUB_ADMIN_USERNAME")
        print("  SCITEX_HUB_ADMIN_EMAIL")
        print("  SCITEX_HUB_ADMIN_PASSWORD")
        sys.exit(1)

    first_name = os.environ.get("SCITEX_HUB_ADMIN_FIRST_NAME", "")
    last_name = os.environ.get("SCITEX_HUB_ADMIN_LAST_NAME", "")
    affiliation = os.environ.get("SCITEX_HUB_ADMIN_AFFILIATION", "")

    try:
        user = User.objects.get(username=username)
        print(f"Found existing user: {user.username}")
        print(f"Current email: {user.email}")

        user.email = new_email
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(new_password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        print("Updated user information:")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.first_name} {user.last_name}")
        print(f"  Staff: {user.is_staff}")
        print(f"  Superuser: {user.is_superuser}")

        # Update or create UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "academic_title": "Researcher",
                "affiliation": affiliation,
                "is_academic": True,
                "allow_messages": True,
                "is_public": True,
            },
        )

        if not created:
            profile.affiliation = affiliation
            profile.save()
            print("Updated UserProfile")
        else:
            print("Created new UserProfile")

        return user

    except User.DoesNotExist:
        print(f"User '{username}' not found")
        return None


if __name__ == "__main__":
    try:
        user = update_user_info()
        if user:
            print("\nUser information updated successfully!")
    except Exception as e:
        print(f"Error updating user: {e}")
        sys.exit(1)
