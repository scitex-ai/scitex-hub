"""
Celery tasks for Project App.

Handles periodic tasks for remote project management.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.project_app.tasks.auto_unmount_inactive_remote_projects",
    max_retries=2,
    soft_time_limit=300,  # 5 minutes
    time_limit=360,  # 6 minutes
)
def auto_unmount_inactive_remote_projects(self):
    """
    Auto-unmount remote projects that have been inactive for > 30 minutes.

    This task runs periodically (e.g., every 10 minutes) to clean up mounted
    remote filesystems that are no longer in use.

    Privacy-preserving design: Files are unmounted when not in active use.

    Returns:
        dict: Statistics about unmounted projects
    """
    try:
        from apps.project_app.models import RemoteProjectConfig
        from apps.project_app.services.remote_project_manager import RemoteProjectManager

        # Find all mounted remote projects
        mounted_configs = RemoteProjectConfig.objects.filter(
            is_mounted=True
        ).select_related('project', 'remote_credential')

        stats = {
            'checked': 0,
            'unmounted': 0,
            'errors': 0,
            'still_active': 0,
        }

        # Inactivity threshold: 30 minutes
        inactive_threshold = timezone.now() - timedelta(minutes=30)

        for config in mounted_configs:
            stats['checked'] += 1

            try:
                # Check if inactive
                last_accessed = config.last_accessed or config.mounted_at

                if not last_accessed:
                    # No access time recorded, assume needs unmount
                    is_inactive = True
                else:
                    is_inactive = last_accessed < inactive_threshold

                if is_inactive:
                    # Unmount inactive project
                    manager = RemoteProjectManager(config.project)
                    success, error = manager.unmount()

                    if success:
                        stats['unmounted'] += 1
                        logger.info(
                            f"✅ Auto-unmounted inactive remote project: "
                            f"{config.project.owner.username}/{config.project.slug} "
                            f"(inactive since {last_accessed})"
                        )
                    else:
                        stats['errors'] += 1
                        logger.warning(
                            f"⚠️ Failed to auto-unmount remote project "
                            f"{config.project.owner.username}/{config.project.slug}: {error}"
                        )
                else:
                    stats['still_active'] += 1

            except Exception as e:
                stats['errors'] += 1
                logger.error(
                    f"Error checking remote project {config.project.owner.username}/{config.project.slug}: {e}",
                    exc_info=True
                )

        # Log summary
        if stats['unmounted'] > 0 or stats['errors'] > 0:
            logger.info(
                f"Auto-unmount task completed: "
                f"checked={stats['checked']}, "
                f"unmounted={stats['unmounted']}, "
                f"still_active={stats['still_active']}, "
                f"errors={stats['errors']}"
            )

        return stats

    except SoftTimeLimitExceeded:
        logger.warning("Auto-unmount task exceeded soft time limit")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in auto-unmount task: {e}", exc_info=True)
        raise


@shared_task(
    bind=True,
    name="apps.project_app.tasks.cleanup_stale_mounts",
    max_retries=2,
    soft_time_limit=300,
    time_limit=360,
)
def cleanup_stale_mounts(self):
    """
    Clean up stale mount points that exist on filesystem but not in database.

    This handles cases where mounts were not properly cleaned up (e.g., server crash).

    Returns:
        dict: Statistics about cleaned up mounts
    """
    try:
        import os
        import subprocess
        from pathlib import Path
        from django.conf import settings
        from apps.project_app.models import RemoteProjectConfig

        stats = {
            'checked': 0,
            'cleaned': 0,
            'errors': 0,
        }

        # Get base mount directory
        mount_base = Path(settings.SCITEX_REMOTE_MOUNT_BASE)

        if not mount_base.exists():
            return stats

        # Get all mount points from database
        active_mounts = set(
            RemoteProjectConfig.objects.filter(
                is_mounted=True,
                mount_point__isnull=False
            ).values_list('mount_point', flat=True)
        )

        # Check each subdirectory in mount base
        for user_dir in mount_base.iterdir():
            if not user_dir.is_dir():
                continue

            for mount_dir in user_dir.iterdir():
                if not mount_dir.is_dir():
                    continue

                stats['checked'] += 1
                mount_path = str(mount_dir)

                # Check if mount exists in database
                if mount_path not in active_mounts:
                    # Stale mount - try to unmount
                    try:
                        # Check if actually mounted
                        result = subprocess.run(
                            ["mountpoint", "-q", mount_path],
                            capture_output=True,
                            timeout=5
                        )

                        if result.returncode == 0:
                            # It's mounted - unmount it
                            subprocess.run(
                                ["fusermount", "-u", mount_path],
                                capture_output=True,
                                timeout=10,
                                check=True
                            )
                            logger.info(f"✅ Cleaned up stale mount: {mount_path}")

                        # Remove directory
                        if mount_dir.exists() and not any(mount_dir.iterdir()):
                            mount_dir.rmdir()
                            stats['cleaned'] += 1

                    except subprocess.TimeoutExpired:
                        stats['errors'] += 1
                        logger.warning(f"⚠️ Timeout cleaning stale mount: {mount_path}")
                    except subprocess.CalledProcessError as e:
                        stats['errors'] += 1
                        logger.warning(f"⚠️ Failed to unmount stale mount {mount_path}: {e}")
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Error cleaning stale mount {mount_path}: {e}")

        if stats['cleaned'] > 0 or stats['errors'] > 0:
            logger.info(
                f"Stale mount cleanup completed: "
                f"checked={stats['checked']}, "
                f"cleaned={stats['cleaned']}, "
                f"errors={stats['errors']}"
            )

        return stats

    except SoftTimeLimitExceeded:
        logger.warning("Cleanup stale mounts task exceeded soft time limit")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in cleanup stale mounts task: {e}", exc_info=True)
        raise
