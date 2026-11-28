#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Celery task: tell the operator about a new inquiry (scitex-hub#1235)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.infra.public_app.tasks.notify_service_inquiry",
    ignore_result=True,
    soft_time_limit=60,
    time_limit=90,
)
def notify_service_inquiry(inquiry_id: int, source: str) -> bool:
    """Look the row up by id (the message carries no personal data) and notify."""
    from apps.infra.public_app.models import ServiceInquiry
    from apps.infra.public_app.services.inquiry_notification import (
        notify_operator_of_inquiry,
    )

    inquiry = ServiceInquiry.objects.filter(pk=inquiry_id).first()
    if inquiry is None:
        logger.error("notify_service_inquiry: inquiry %s no longer exists", inquiry_id)
        return False
    return notify_operator_of_inquiry(inquiry, source=source)
