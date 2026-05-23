#!/usr/bin/env python
"""
Reset Database with Enhanced Group and Permission System

This script will:
1. Delete the existing database
2. Remove all migration files (except __init__.py)
3. Create fresh migrations
4. Apply migrations to create new database schema
5. Create a superuser account

Run this script when you need a clean database with the new permission system.
"""

import os
from pathlib import Path

import django

# Setup Django
os.environ.setdefault(
    "SCITEX_HUB_DJANGO_SETTINGS_MODULE", "config.settings.development"
)
django.setup()


def reset_database():
    """Reset the database and migrations"""
    print("🔄 Resetting SciTeX Hub database with new permission system...")

    # 1. Remove database file
    db_path = Path("db.sqlite3")
    if db_path.exists():
        print("  ✓ Removing existing database...")
        os.remove(db_path)

    # 2. Remove migration files (keep __init__.py)
    apps_to_reset = [
        "apps/workspace/figrecipe_app/migrations",
        "apps/workspace/console_app/migrations",
        "apps/workspace/writer_app/migrations",
        "apps/workspace/scholar_app/migrations",
        "apps/workspace/repo_app/migrations",
        "apps/workspace/docs_app/migrations",
        "apps/workspace/discovery_app/migrations",
        "apps/infra/project_app/migrations",
        "apps/infra/public_app/migrations",
        "apps/infra/accounts_app/migrations",
        "apps/infra/gitea_app/migrations",
    ]

    for migration_dir in apps_to_reset:
        migration_path = Path(migration_dir)
        if migration_path.exists():
            print(f"  ✓ Cleaning migrations in {migration_dir}...")
            for file in migration_path.glob("*.py"):
                if file.name != "__init__.py":
                    os.remove(file)

    # 3. Create fresh migrations
    print("  ✓ Creating fresh migrations...")
    os.system("python manage.py makemigrations")

    # 4. Apply migrations
    print("  ✓ Creating database schema...")
    os.system("python manage.py migrate")

    # 5. Create superuser
    print("  ✓ Creating superuser account...")
    from django.contrib.auth.models import User

    from apps.infra.workspace_app.models import UserProfile

    # Create superuser from env vars
    admin_user_name = os.environ.get("SCITEX_HUB_ADMIN_USERNAME", "admin")
    admin_email = os.environ.get("SCITEX_HUB_ADMIN_EMAIL", "admin@scitex.ai")
    admin_password = os.environ.get("SCITEX_HUB_ADMIN_PASSWORD", "admin123")

    if not User.objects.filter(username=admin_user_name).exists():
        admin_user = User.objects.create_superuser(
            username=admin_user_name,
            email=admin_email,
            password=admin_password,
            first_name="SciTeX",
            last_name="Administrator",
        )

        # Create profile for admin
        profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                "bio": "SciTeX Hub Administrator",
                "institution": "SciTeX Hub",
                "academic_title": "System Administrator",
                "department": "Platform Operations",
                "research_interests": "Research platform development and management",
            },
        )
        print(f"    ✓ Created superuser: {admin_user_name}")

    # 6. Create sample data for testing
    print("  ✓ Creating sample research data...")
    create_sample_data()

    print("\n🎉 Database reset complete!")
    print("📝 You can now login with:")
    print(f"   Username: {admin_user_name}")
    print("   Password: <SCITEX_HUB_ADMIN_PASSWORD>")
    print("\n🚀 Enhanced group and permission system is ready!")


def create_sample_data():
    """Create sample organizations, groups, and projects for testing"""
    from django.contrib.auth.models import User

    from apps.infra.workspace_app.models import (
        Organization,
        Project,
        ProjectMembership,
        ResearchGroup,
    )

    # Create sample organization
    org, created = Organization.objects.get_or_create(
        name="University of Tokyo",
        defaults={"description": "Leading research university in Japan"},
    )

    # Create sample users
    users_data = [
        {
            "username": "prof_ikegaya",
            "email": "ikegaya@edu.u-tokyo.ac.jp",
            "first_name": "Yuji",
            "last_name": "Ikegaya",
            "role": "pi",
        },
        {
            "username": "postdoc_tanaka",
            "email": "tanaka@alumni.u-tokyo.ac.jp",
            "first_name": "Hiroshi",
            "last_name": "Tanaka",
            "role": "postdoc",
        },
        {
            "username": "phd_sato",
            "email": "sato@g.ecc.u-tokyo.ac.jp",
            "first_name": "Yuki",
            "last_name": "Sato",
            "role": "phd",
        },
    ]

    created_users = {}
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data["username"],
            defaults={
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "password": "pbkdf2_sha256$600000$test123$dummy_hash_for_demo",  # Password: test123
            },
        )
        created_users[user_data["role"]] = user

    # Create research group
    if created_users.get("pi"):
        group, created = ResearchGroup.objects.get_or_create(
            name="Ikegaya Laboratory",
            organization=org,
            principal_investigator=created_users["pi"],
            defaults={
                "description": "Computational Neuroscience and Brain-Machine Interface Research",
                "is_public": True,
                "allow_external_collaborators": True,
            },
        )

        # Add group members
        if created_users.get("postdoc"):
            from apps.infra.workspace_app.models import ResearchGroupMembership

            ResearchGroupMembership.objects.get_or_create(
                user=created_users["postdoc"],
                group=group,
                defaults={
                    "role": "postdoc",
                    "can_create_projects": True,
                    "can_invite_collaborators": True,
                },
            )

        if created_users.get("phd"):
            from apps.infra.workspace_app.models import ResearchGroupMembership

            ResearchGroupMembership.objects.get_or_create(
                user=created_users["phd"],
                group=group,
                defaults={
                    "role": "phd",
                    "can_create_projects": True,
                    "can_invite_collaborators": False,
                },
            )

        # Create sample project
        project, created = Project.objects.get_or_create(
            name="Brain-Computer Interface for Motor Recovery",
            owner=created_users["pi"],
            defaults={
                "description": "Developing BCI technology for stroke rehabilitation using machine learning and neural signal processing.",
                "hypotheses": "We hypothesize that real-time neural feedback through BCI can significantly improve motor function recovery in stroke patients.",
                "research_group": group,
                "organization": org,
                "status": "active",
                "progress": 45,
            },
        )

        # Add project collaborators with different roles
        if created_users.get("postdoc"):
            ProjectMembership.objects.get_or_create(
                user=created_users["postdoc"],
                project=project,
                defaults={
                    "role": "editor",
                    "can_read_files": True,
                    "can_write_files": True,
                    "can_delete_files": True,
                    "can_manage_collaborators": True,
                    "can_edit_metadata": True,
                    "can_run_analysis": True,
                    "access_granted_by": created_users["pi"],
                },
            )

        if created_users.get("phd"):
            ProjectMembership.objects.get_or_create(
                user=created_users["phd"],
                project=project,
                defaults={
                    "role": "collaborator",
                    "can_read_files": True,
                    "can_write_files": True,
                    "can_delete_files": False,
                    "can_manage_collaborators": False,
                    "can_edit_metadata": False,
                    "can_run_analysis": True,
                    "access_granted_by": created_users["pi"],
                },
            )

        print(f"    ✓ Created research group: {group.name}")
        print(f"    ✓ Created sample project: {project.name}")
        print(f"    ✓ Added {len(created_users)} sample users with roles")


if __name__ == "__main__":
    pass
