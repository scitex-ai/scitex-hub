#!/usr/bin/env python
"""
Create initial user and profile for SciTeX Hub platform.

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


def create_initial_user():
    """Create the initial user and profile"""
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
    affiliation = os.environ.get("SCITEX_HUB_ADMIN_AFFILIATION", "")

    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists.")
        user = User.objects.get(username=username)
        print(f"Existing user: {user.username} ({user.email})")
        return user

    # Create the user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=True,
        is_superuser=True,
    )

    # Create or update UserProfile
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

    if created:
        print(f"Created UserProfile for {username}")
    else:
        print(f"UserProfile already exists for {username}")

    print(f"Successfully created user: {username}")
    print(f"Email: {email}")
    print(f"Admin access: {user.is_staff}")
    print(f"Superuser: {user.is_superuser}")
    print(f"Profile created: {created}")

    return user


if __name__ == "__main__":
    try:
        user = create_initial_user()
        print("\nDatabase initialization completed successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")
        sys.exit(1)
