import logging

from django.contrib.auth.models import User
from django.contrib.auth.signals import (
    user_logged_in,  # noqa: F401 - used in decorator below
)
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


@receiver(user_logged_in)
def ensure_home_project_on_login(sender, user, request, **kwargs):
    """Ensure home project exists every time a user logs in."""
    ensure_home_project(user)


def create_default_project_for_user(user):
    """Create a default project for newly created users"""
    ensure_home_project(user)


def ensure_home_project(user):
    """Ensure user has a dotfiles project. Creates one if missing.

    Idempotent — safe to call on every login.
    The dotfiles project is a git-trackable, private, undeletable project
    for managing shell configs (bashrc, vimrc, gitconfig, etc.).
    """
    from apps.project_app.models import Project

    try:
        if Project.objects.filter(owner=user, is_home=True).exists():
            return

        dotfiles_project = Project.objects.create(
            name="dotfiles",
            slug="dotfiles",
            description=f"Shell configuration for {user.username}",
            owner=user,
            visibility="private",
            is_home=True,
        )

        # Set as last active if user has no active project
        if hasattr(user, "profile") and not user.profile.last_active_repository:
            user.profile.last_active_repository = dotfiles_project
            user.profile.save()

        logger.info(f"Created dotfiles project for {user.username}")

    except Exception as e:
        logger.error(
            f"Error creating dotfiles project for user {user.username}: {str(e)}"
        )
