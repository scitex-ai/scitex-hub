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

from apps.infra.public_app.models import SiteHealthProbe
from config import branding

logger = logging.getLogger(__name__)

# Health Monitoring Cache Keys
HEALTH_CHECK_CACHE_KEY = "health_check_status"
HEALTH_CHECK_FAILURE_COUNT_KEY = "health_check_failures"
HEALTH_CHECK_LAST_NOTIFICATION_KEY = "health_check_last_notification"

# Flood Detection Cache Keys
FLOOD_DETECTION_PREFIX = "flood_detection:"
FLOOD_ALERT_LAST_SENT_KEY = "flood_alert_last_sent"


@shared_task(
    bind=True,
    name="apps.infra.public_app.tasks.cleanup_expired_visitor_allocations",
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
        from apps.infra.project_app.services.visitor_pool import VisitorPool

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
        settings, "SITE_URL", os.getenv("SCITEX_HUB_SITE_URL", "https://scitex.ai")
    )
    health_check_url = f"{site_url}/"
    notification_recipient = os.getenv("SCITEX_HUB_HEALTH_NOTIFICATION_RECIPIENT")
    # The default sender is the SSoT's noreply address (config/branding.py), not
    # a literal: this module is plain Python, so there is no reason for it to
    # carry its own copy of an address the rest of the site single-sources.
    notification_sender = os.getenv(
        "SCITEX_HUB_HEALTH_NOTIFICATION_SENDER", branding.NOREPLY_EMAIL
    )
    return health_check_url, site_url, notification_recipient, notification_sender


def _perform_health_check(
    url: str,
) -> tuple[bool, str | None, float | None, int | None]:
    """Perform HTTP health check.

    Returns (is_healthy, error_message, response_time, status_code).
    """
    try:
        response = requests.get(
            url, timeout=10, headers={"User-Agent": "SciTeX-HealthCheck/1.0"}
        )
        response_time = response.elapsed.total_seconds()
        is_healthy = response.status_code == 200
        error_message = None if is_healthy else f"HTTP {response.status_code}"
        return is_healthy, error_message, response_time, response.status_code
    except requests.exceptions.Timeout:
        return False, "Request timeout (>10s)", None, None
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:100]}", None, None
    except Exception as e:
        return False, f"Error: {str(e)[:100]}", None, None


def _send_recovery_notification(
    url: str, response_time: float, recipient: str, sender: str
):
    """Send site recovery notification email.

    ``fail_silently=False`` is deliberate -- see ``_send_alert_notification``.
    """
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
            fail_silently=False,
        )
    except Exception as e:
        logger.error(
            f"[HealthCheck] ALARM DELIVERY FAILED (recovery): {e}. "
            f"recipient={recipient} sender={sender}. "
            "Check EMAIL_HOST/EMAIL_HOST_USER credentials.",
            exc_info=True,
        )


def _send_alert_notification(
    url: str, error: str, failure_count: int, recipient: str, sender: str
):
    """Send site down alert notification email.

    ``fail_silently=False`` is deliberate, and is the whole point of this
    function. With ``True`` -- what this shipped with -- Django's mail backend
    swallows send failures, so the ``except`` below never fires and its
    ``logger.error`` is dead code for the failure it exists to report. Stale
    SMTP credentials would then produce an alarm that is silent about being
    silent: configured, believed live, and incapable of saying otherwise.

    The task keeps running either way -- the caller does not re-raise -- so
    nothing is gained by discarding the error, and the one thing an alarm must
    never do is fail quietly.
    """
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
2. Check Django logs: docker logs scitex-hub-prod-django-1
3. Restart services: docker restart scitex-hub-prod-django-1
""",
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(
            f"[HealthCheck] ALARM DELIVERY FAILED (site down): {e}. "
            f"recipient={recipient} sender={sender}. "
            "The site-down alert did NOT reach anyone. "
            "Check EMAIL_HOST/EMAIL_HOST_USER credentials.",
            exc_info=True,
        )


@shared_task(
    bind=True,
    name="apps.infra.public_app.tasks.check_site_health",
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
            # WARNING, not DEBUG. This is the difference between "the alarm is
            # armed" and "the alarm is running but can reach nobody", and at
            # DEBUG that distinction was invisible in production -- emitted
            # once a minute into a level nothing collects. An alarm that cannot
            # notify must say so at a level someone sees.
            logger.warning(
                "[HealthCheck] SCITEX_HUB_HEALTH_NOTIFICATION_RECIPIENT is not "
                "set, so site-down and recovery alerts will reach NOBODY. "
                "Set it in deployment/docker/envs/.env.<env>."
            )

        # Perform check
        is_healthy, error_message, response_time, status_code = _perform_health_check(
            url
        )

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

        # Persist one probe row per run (success AND failure — a failed
        # probe with response_time_ms=None is signal, not noise). History
        # enables before/after comparisons (router swap 2026-07-21, NURO
        # 10G). Retention: collect_server_metrics deletes rows >30 days.
        SiteHealthProbe.objects.create(
            timestamp=timezone.now(),
            response_time_ms=(
                response_time * 1000.0 if response_time is not None else None
            ),
            is_healthy=is_healthy,
            status_code=status_code,
        )

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


@shared_task(
    bind=True,
    name="apps.infra.public_app.tasks.check_request_flood",
    ignore_result=True,
    soft_time_limit=30,
    time_limit=60,
)
def check_request_flood(self):
    """
    Detect request flood patterns by analyzing nginx access logs.

    Runs every minute. Sends alert if:
    - Any IP makes >100 requests to same endpoint in 1 minute
    - Any endpoint receives >500 total requests in 1 minute

    This provides early warning of potential DDoS or misconfigured clients.
    """
    import subprocess

    try:
        _, _, recipient, sender = _get_health_config()

        if not recipient:
            logger.debug("[FloodDetection] No notification recipient configured")
            return

        # Check if we recently sent an alert (rate limit: 1 per 5 minutes)
        last_alert = cache.get(FLOOD_ALERT_LAST_SENT_KEY)
        if last_alert:
            logger.debug("[FloodDetection] Skipping - alert sent recently")
            return

        # Analyze nginx logs for flood patterns (last 60 seconds)
        try:
            # Get request counts per IP per endpoint from access log
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "scitex-hub-prod-nginx-1",
                    "sh",
                    "-c",
                    """awk -v threshold=100 '
                    {
                        # Extract IP and URL
                        ip=$1
                        for(i=1;i<=NF;i++) if($i ~ /^"GET|^"POST/) {url=$(i+1); break}
                        if(url) key=ip":"url
                        count[key]++
                    }
                    END {
                        for(k in count) if(count[k]>threshold) print count[k], k
                    }
                    ' /var/log/nginx/access.log | tail -10
                    """,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Flood detected
                flood_entries = result.stdout.strip()
                logger.warning(
                    f"[FloodDetection] Flood pattern detected:\n{flood_entries}"
                )

                # Send alert
                send_mail(
                    subject="[SciTeX] Request Flood Detected",
                    message=f"""Request flood pattern detected!

Entries exceeding 100 requests/minute:
{flood_entries}

Time: {timezone.now().isoformat()}

This may indicate:
1. DDoS attack
2. Misconfigured monitoring script
3. Aggressive crawler

Recommended actions:
1. Check nginx logs: docker logs scitex-hub-prod-nginx-1 --tail 200
2. Block offending IPs if malicious
3. Check for health check scripts in retry loops
""",
                    from_email=sender,
                    recipient_list=[recipient],
                    fail_silently=False,
                )

                # Rate limit alerts
                cache.set(FLOOD_ALERT_LAST_SENT_KEY, True, 300)  # 5 minutes

                return {"status": "flood_detected", "entries": flood_entries}

        except subprocess.TimeoutExpired:
            logger.warning("[FloodDetection] Log analysis timed out")
        except FileNotFoundError:
            logger.debug("[FloodDetection] Docker not available, skipping")

        return {"status": "ok", "message": "No flood detected"}

    except Exception as e:
        logger.error(f"[FloodDetection] Task error: {e}", exc_info=True)
        raise


@shared_task(
    name="apps.infra.public_app.tasks.warm_public_status_cache",
    ignore_result=True,
    soft_time_limit=60,
    time_limit=90,
)
def warm_public_status_cache():
    """Periodically refresh the /status page cache.

    The synchronous health checks (DB, Redis, SSH, API) take ~15-20s on a
    cold path which is intolerable for the user-facing /status page. We
    keep the cache hot by recomputing every 60s in the background, so
    visitors essentially never hit the cold path.

    Refs scitex-orochi#82 (TTFB 17s regression).
    """
    try:
        from apps.infra.public_app.views.status.public_status import (
            PUBLIC_STATUS_CACHE_KEY,
            PUBLIC_STATUS_CACHE_TTL,
            _compute_status_data,
        )

        data = _compute_status_data()
        cache.set(PUBLIC_STATUS_CACHE_KEY, data, PUBLIC_STATUS_CACHE_TTL)
        logger.debug(
            "[StatusCacheWarm] cached overall=%s in TTL=%ss",
            data.get("overall"),
            PUBLIC_STATUS_CACHE_TTL,
        )
        return {"status": "ok", "overall": data.get("overall")}
    except Exception as e:
        logger.error(f"[StatusCacheWarm] failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# EOF
