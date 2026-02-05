#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Site health monitoring and visitor cleanup tasks."""

from __future__ import annotations

import logging
import os

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

# Health Monitoring Cache Keys
HEALTH_CHECK_CACHE_KEY = "health_check_status"
HEALTH_CHECK_FAILURE_COUNT_KEY = "health_check_failures"
HEALTH_CHECK_LAST_NOTIFICATION_KEY = "health_check_last_notification"


@shared_task(
    bind=True,
    name="apps.public_app.tasks.cleanup_expired_visitor_allocations",
    ignore_result=True,
    soft_time_limit=30,
    time_limit=60,
)
def cleanup_expired_visitor_allocations(self):
    """
    Clean up expired visitor slot allocations.

    Runs periodically (every 5 minutes) to free up visitor slots whose
    sessions have expired.

    Returns:
        int: Number of slots freed
    """
    try:
        from apps.project_app.services.visitor_pool import VisitorPool

        freed_count = VisitorPool.cleanup_expired_allocations()

        if freed_count > 0:
            logger.info(
                f"[VisitorPool] Cleaned up {freed_count} expired visitor allocations"
            )
        else:
            logger.debug("[VisitorPool] No expired allocations to clean up")

        return freed_count

    except Exception as e:
        logger.error(
            f"[VisitorPool] Failed to clean up expired allocations: {e}", exc_info=True
        )
        raise


def _get_health_config() -> tuple[str, str, str | None, str]:
    """Get health check configuration from settings/env."""
    site_url = getattr(
        settings, "SITE_URL", os.getenv("SCITEX_CLOUD_SITE_URL", "https://scitex.ai")
    )
    health_check_url = f"{site_url}/"
    notification_recipient = os.getenv("SCITEX_CLOUD_HEALTH_NOTIFICATION_RECIPIENT")
    notification_sender = os.getenv(
        "SCITEX_CLOUD_HEALTH_NOTIFICATION_SENDER", "noreply@scitex.ai"
    )
    return health_check_url, site_url, notification_recipient, notification_sender


def _perform_health_check(url: str) -> tuple[bool, str | None, float | None]:
    """Perform HTTP health check and return (is_healthy, error_message, response_time)."""
    try:
        response = requests.get(
            url, timeout=10, headers={"User-Agent": "SciTeX-HealthCheck/1.0"}
        )
        response_time = response.elapsed.total_seconds()
        is_healthy = response.status_code == 200
        error_message = None if is_healthy else f"HTTP {response.status_code}"
        return is_healthy, error_message, response_time
    except requests.exceptions.Timeout:
        return False, "Request timeout (>10s)", None
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:100]}", None
    except Exception as e:
        return False, f"Error: {str(e)[:100]}", None


def _send_recovery_notification(
    url: str, response_time: float, recipient: str, sender: str
):
    """Send site recovery notification email."""
    try:
        send_mail(
            subject="[SciTeX] Site Recovered",
            message=f"""SciTeX is back online!

URL: {url}
Response Time: {response_time:.2f}s
Time: {timezone.now().isoformat()}

The site is now responding normally.
""",
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"[HealthCheck] Failed to send recovery email: {e}")


def _send_alert_notification(
    url: str, error: str, failure_count: int, recipient: str, sender: str
):
    """Send site down alert notification email."""
    try:
        send_mail(
            subject="[SciTeX] Site Down Alert",
            message=f"""SciTeX is experiencing issues!

URL: {url}
Error: {error}
Consecutive Failures: {failure_count}
Time: {timezone.now().isoformat()}

Please check the server status.

Possible actions:
1. Check Docker containers: docker ps
2. Check Django logs: docker logs scitex-cloud-prod-django-1
3. Restart services: docker restart scitex-cloud-prod-django-1
""",
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"[HealthCheck] Failed to send alert email: {e}")


@shared_task(
    bind=True,
    name="apps.public_app.tasks.check_site_health",
    ignore_result=True,
    soft_time_limit=30,
    time_limit=60,
)
def check_site_health(self):
    """
    Check if the site is accessible and notify admin on failures.

    Runs every minute. Sends notification when:
    - Site becomes unhealthy (3 consecutive failures)
    - Site recovers after being unhealthy
    """
    failure_threshold = 3

    try:
        url, _, recipient, sender = _get_health_config()

        if not recipient:
            logger.debug(
                "[HealthCheck] SCITEX_CLOUD_HEALTH_NOTIFICATION_RECIPIENT not set"
            )

        # Perform check
        is_healthy, error_message, response_time = _perform_health_check(url)

        # Get previous state
        prev_status = cache.get(HEALTH_CHECK_CACHE_KEY, "unknown")
        failure_count = cache.get(HEALTH_CHECK_FAILURE_COUNT_KEY, 0)

        # Update state based on result
        if is_healthy:
            new_status = "healthy"
            cache.set(HEALTH_CHECK_FAILURE_COUNT_KEY, 0, timeout=3600)

            if prev_status == "unhealthy":
                logger.info("[HealthCheck] Site recovered!")
                if recipient and response_time:
                    _send_recovery_notification(url, response_time, recipient, sender)
        else:
            failure_count += 1
            cache.set(HEALTH_CHECK_FAILURE_COUNT_KEY, failure_count, timeout=3600)

            if failure_count >= failure_threshold:
                new_status = "unhealthy"
                if prev_status != "unhealthy":
                    logger.error(f"[HealthCheck] Site is DOWN! Error: {error_message}")
                    if recipient:
                        _send_alert_notification(
                            url, error_message, failure_count, recipient, sender
                        )
            else:
                new_status = "degraded"
                logger.warning(
                    f"[HealthCheck] Failed ({failure_count}/{failure_threshold}): {error_message}"
                )

        cache.set(HEALTH_CHECK_CACHE_KEY, new_status, timeout=3600)

        return {
            "status": new_status,
            "is_healthy": is_healthy,
            "response_time": response_time,
            "failure_count": failure_count,
            "error": error_message,
        }

    except Exception as e:
        logger.error(f"[HealthCheck] Task error: {e}", exc_info=True)
        raise


# EOF
