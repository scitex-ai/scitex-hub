import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created (if not already exists)"""
    if created:
        profile, _ = UserProfile.objects.get_or_create(user=instance)

        # Create Gitea user account automatically
        try:
            from apps.gitea_app.services.gitea_sync_service import (
                ensure_gitea_user_exists,
            )

            ensure_gitea_user_exists(instance)
            logger.info(f"Gitea user auto-created for {instance.username}")
        except Exception as e:
            logger.warning(
                f"Failed to auto-create Gitea user for {instance.username}: {e}"
            )
            # Don't fail user creation if Gitea sync fails

        # Provision OS-level Linux account and data directory ownership.
        # Non-fatal: log warnings but never break user creation.
        try:
            from apps.accounts_app.services.unix_user import (
                enforce_data_dir_ownership,
                ensure_linux_account,
                get_unix_uid,
            )

            ensure_linux_account(instance)
            enforce_data_dir_ownership(instance)
            uid = get_unix_uid(instance)
            profile.unix_uid = uid
            profile.unix_gid = uid
            profile.save(update_fields=["unix_uid", "unix_gid"])
        except Exception as exc:
            logger.warning(
                f"Failed to provision Linux account for {instance.username}: {exc}"
            )

        # Create a default project for the new user
        create_default_project_for_user(instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, "profile"):
        instance.profile.save()


def create_default_project_for_user(user):
    """Create a default project for newly created users"""
    from apps.project_app.models import Project

    try:
        # Check if user already has projects
        if Project.objects.filter(owner=user).exists():
            return

        # Create a default project for the user
        # The URL will be /<username>/default-project/ (no numeric suffix needed)
        # because uniqueness is per-owner, not global
        default_project_name = "default-project"
        default_project = Project.objects.create(
            name=default_project_name,
            slug=default_project_name,  # Simple slug without numeric suffix
            description=f"Default project for {user.username}",
            owner=user,
            visibility="private",
        )

        # Set as last active repository
        user.profile.last_active_repository = default_project
        user.profile.save()

    except Exception as e:
        # Log error but don't break user creation
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Error creating default project for user {user.username}: {str(e)}"
        )
