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
            from apps.infra.gitea_app.services.gitea_sync_service import (
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
            from apps.infra.accounts_app.services.unix_user import (
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


def _adopt_landing_project(user, *, fallback):
    """Point a profile with no active project at the best one it owns.

    The home (dotfiles) project is shell configuration — bashrc, gitconfig,
    screenrc. It is a real feature for a signed-in user and a terrible first
    screen for anyone else, because landing there shows a stranger our shell
    dotfiles and nothing about research.

    Measured on production 2026-08-16: every visitor workspace already holds
    BOTH projects on disk --

        proj/default-project/   figures/confusion_matrix.png, figures/digit_grid.png,
                                data/digits_sample.csv, scripts/reproduce_figures.py
        proj/dotfiles/          install.sh, bash_profile, screenrc, gitconfig

    -- and the visitor was landed on the second one, so /apps/writer/ rendered
    "dotfiles · Writer", 0 words and a blank manuscript while the seeded demo
    sat unopened beside it. The content was never missing; the pointer was
    wrong.

    So prefer any NON-home project the user owns, and fall back to the home
    project only when there is genuinely nothing else. Oldest-first, so the
    provisioned demo wins over anything created later in the session.
    """
    if not hasattr(user, "profile") or user.profile.last_active_repository:
        return

    from apps.infra.project_app.models import Project

    landing = (
        Project.objects.filter(owner=user, is_home=False).order_by("id").first()
        or fallback
    )
    user.profile.last_active_repository = landing
    user.profile.save()


def ensure_home_project(user):
    """Ensure user has a dotfiles project. Creates one if missing.

    Idempotent — safe to call on every login.
    The dotfiles project is a git-trackable, private, undeletable project
    for managing shell configs (bashrc, vimrc, gitconfig, etc.).

    It is NOT the landing project: see :func:`_adopt_landing_project`.
    """
    from apps.infra.project_app.models import Project

    try:
        existing_home = Project.objects.filter(owner=user, is_home=True).first()
        if existing_home is not None:
            # The home project is already there, but the profile may still have
            # no landing project at all -- a user provisioned before the demo
            # project existed, for instance. Adopting here as well means a login
            # repairs that, instead of the repair being reachable only on the
            # one call that happens to create the home project.
            _adopt_landing_project(user, fallback=existing_home)
            return

        dotfiles_project = Project.objects.create(
            name="dotfiles",
            slug="dotfiles",
            description=f"Shell configuration for {user.username}",
            owner=user,
            visibility="private",
            is_home=True,
        )

        _adopt_landing_project(user, fallback=dotfiles_project)

        logger.info(f"Created dotfiles project for {user.username}")

    except Exception as e:
        logger.error(
            f"Error creating dotfiles project for user {user.username}: {str(e)}"
        )
