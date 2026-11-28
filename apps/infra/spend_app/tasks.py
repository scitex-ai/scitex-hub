"""Celery beat entry points (scheduled in config/settings/settings_celery.py)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("scitex")


def _sweep(active_only: bool) -> dict:
    from .services import dunning, enforcement

    swept = failed = 0
    for user in enforcement.users_to_sweep(active_only=active_only).distinct():
        try:
            enforcement.sweep_user(user)
            swept += 1
        except Exception:
            failed += 1
            logger.exception("spend sweep failed for user %s", user.pk)
    reminded = dunning.sweep_all()
    result = {"swept": swept, "failed": failed, "past_due": reminded}
    if failed:
        logger.error("spend sweep: %s", result)
    return result


@shared_task(name="apps.infra.spend_app.tasks.sweep_active_spend")
def sweep_active_spend():
    """Every 5 min: accounts with work in flight or a payment problem."""
    return _sweep(active_only=True)


@shared_task(name="apps.infra.spend_app.tasks.sweep_all_spend")
def sweep_all_spend():
    """Hourly: every recently active account (storage-only usage included)."""
    return _sweep(active_only=False)
