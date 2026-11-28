import logging

from django.contrib.auth.models import User
from django.contrib.auth.signals import (
    user_logged_in,  # noqa: F401 - used in decorator below
)
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import UserProfile

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def remember_activation_state(sender, instance, update_fields=None, **kwargs):
    """Record whether a saved user was active before this save.

    External accounts are provisioned when a user BECOMES active (see
    ``create_user_profile``), so the previous state is needed to tell an
    activation from any other save. Saves that do not touch ``is_active``
    (e.g. ``last_login`` on every sign-in) skip the lookup.
    """
    if instance.pk is None:
        instance._was_active = False
        return
    if update_fields is not None and "is_active" not in update_fields:
        return
    instance._was_active = bool(
        User.objects.filter(pk=instance.pk)
        .values_list("is_active", flat=True)
        .first()
    )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create the UserProfile, and provision external accounts on activation.

    A new account is inactive until its owner verifies the e-mail address.
    The Gitea account and the Linux account are created only once the user
    is active: at creation for accounts that start active (admin-created,
    verified social sign-in), otherwise when verification activates them.
    An unverified sign-up therefore leaves nothing outside the database.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)

    became_active = instance.is_active and not getattr(instance, "_was_active", True)
    # The in-memory instance now reflects the stored state, so a later save
    # of the same object that skips the lookup is not seen as an activation.
    instance._was_active = instance.is_active
    if became_active:
        provision_external_accounts(instance)


def provision_external_accounts(user):
    """Create the user's Gitea and Linux accounts (idempotent, non-fatal)."""
    profile, _ = UserProfile.objects.get_or_create(user=user)

    try:
        from apps.infra.gitea_app.services.gitea_sync_service import (
            ensure_gitea_user_exists,
        )

        ensure_gitea_user_exists(user)
        logger.info(f"Gitea user ensured for {user.username}")
    except Exception as e:
        logger.warning(f"Failed to create Gitea user for {user.username}: {e}")
        # Don't fail activation if Gitea sync fails; repository creation
        # calls ensure_gitea_user_exists again.

    # Provision OS-level Linux account and data directory ownership.
    # Non-fatal: log warnings but never break activation.
    try:
        from apps.infra.accounts_app.services.unix_user import (
            enforce_data_dir_ownership,
            ensure_linux_account,
            get_unix_uid,
        )

        ensure_linux_account(user)
        enforce_data_dir_ownership(user)
        uid = get_unix_uid(user)
        profile.unix_uid = uid
        profile.unix_gid = uid
        profile.save(update_fields=["unix_uid", "unix_gid"])
    except Exception as exc:
        logger.warning(f"Failed to provision Linux account for {user.username}: {exc}")

    # Operator 2026-09-27: dotfiles seeding dropped. The user is an
    # ordinary unix account (shell prefs come from ~/.bashrc etc.);
    # the only contract is the proj dir. New users start empty and the
    # first-run steps point them at /new/.


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, "profile"):
        instance.profile.save()


@receiver(user_logged_in)
def ensure_home_project_on_login(sender, user, request, **kwargs):
    """Kept for backward compatibility; dotfiles seeding was dropped
    (operator 2026-09-27). Existing dotfiles projects are untouched."""
    return


def ensure_home_project(user):
    """Ensure user has a dotfiles project. Creates one if missing.

    Idempotent — safe to call on every login.
    The dotfiles project is a git-trackable, private, undeletable project
    for managing shell configs (bashrc, vimrc, gitconfig, etc.).

    Creating it does NOT make it the user's project: it is shell
    configuration, so it must never become the active/landing project on its
    own (card hub-first-login-project-workspace-onboarding-20260917). The user
    chooses a project on first login, or the workspace asks —
    ``accounts_app.onboarding`` owns that rule.
    """
    from apps.infra.project_app.models import Project

    try:
        existing_home = Project.objects.filter(owner=user, is_home=True).first()
        if existing_home is not None:
            return

        Project.objects.create(
            name="dotfiles",
            slug="dotfiles",
            description=f"Shell configuration for {user.username}",
            owner=user,
            visibility="private",
            is_home=True,
        )

        logger.info(f"Created dotfiles project for {user.username}")

    except Exception as e:
        logger.error(
            f"Error creating dotfiles project for user {user.username}: {str(e)}"
        )
