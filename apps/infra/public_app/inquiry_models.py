#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inbound inquiries from /services/ and /contact/ (re-exported by models.py)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceInquiry(models.Model):
    """A services-page or contact-page inquiry (問い合わせ).

    Every submission is PERSISTED here first, so nothing is lost whatever
    happens to the notification afterwards. The operator is then notified
    through scitex-notification (services/inquiry_notification.py). This is an
    inquiry entry point only: no billing/前受金 anything is implemented here.

    scitex-hub#1235 added the lifecycle: who handled it and when (so
    first-response time is a number), and whether the operator was ever told.
    """

    name = models.CharField(max_length=120, verbose_name="お名前")
    affiliation = models.CharField(max_length=200, blank=True, verbose_name="ご所属")
    # The free-text 相談内容 — what the person wants to hire us for.
    request = models.TextField(verbose_name="ご相談内容")
    # Optional 予算感 kept as free text (bands, "未定" etc.), never a hard number.
    budget = models.CharField(max_length=120, blank=True, verbose_name="ご予算感")
    handled = models.BooleanField(default=False, verbose_name="対応済み")
    created_at = models.DateTimeField(auto_now_add=True)

    handled_at = models.DateTimeField(null=True, blank=True, verbose_name="対応日時")
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="対応者",
    )
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="通知日時",
        help_text="When the operator notification was accepted for delivery.",
    )
    notify_error = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="通知エラー",
        help_text="Why the last notification attempt failed (error class only).",
    )

    class Meta:
        app_label = "public_app"
        ordering = ["-created_at"]
        verbose_name = "Service Inquiry"
        verbose_name_plural = "Service Inquiries"
        indexes = [
            models.Index(
                fields=["handled", "-created_at"], name="public_app_inq_open_idx"
            )
        ]

    def __str__(self):
        who = self.affiliation or "-"
        return f"{self.name} ({who}) {self.created_at:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        # The handled flag and its timestamp cannot disagree, however the flag
        # was changed (admin action, list_editable checkbox, shell).
        if self.handled and self.handled_at is None:
            self.handled_at = timezone.now()
        elif not self.handled:
            self.handled_at = None
            self.handled_by = None
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "handled" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"handled_at", "handled_by"}
        super().save(*args, **kwargs)

    @property
    def first_response_time(self):
        """created -> handled, or None while the inquiry is open."""
        if self.handled_at is None or self.created_at is None:
            return None
        return self.handled_at - self.created_at

    def mark_handled(self, user=None):
        """Close the inquiry, recording who closed it."""
        self.handled = True
        if user is not None and getattr(user, "is_authenticated", False):
            self.handled_by = user
        self.save(update_fields=["handled", "handled_at", "handled_by"])

    def reopen(self):
        self.handled = False
        self.save(update_fields=["handled", "handled_at", "handled_by"])

    def record_notification(self, *, ok: bool, error: str = ""):
        """Store the outcome of one notification attempt on the row."""
        if ok:
            self.notified_at = timezone.now()
            self.notify_error = ""
        else:
            self.notify_error = (error or "unknown")[:120]
        type(self).objects.filter(pk=self.pk).update(
            notified_at=self.notified_at, notify_error=self.notify_error
        )
