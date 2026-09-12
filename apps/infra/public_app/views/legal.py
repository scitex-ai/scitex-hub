#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/legal.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/legal.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Legal Pages Views

Handles contact, privacy policy, terms of use, cookie policy, and the
特定商取引法に基づく表記 (Specified Commercial Transactions Act) pages.
"""

from django.conf import settings
from django.shortcuts import render
from django.utils import translation
from ..pricing import annotate_jpy_reference, get_usd_jpy_rate, published_price_rows


def donate(request):
    """Donate page - support SciTeX development."""
    return render(request, "public_app/legal/donate.html")


def contact(request):
    """Contact page — three channels + a direct inquiry form.

    The form persists to the SAME ServiceInquiry model /services/ uses
    (the cash-runway inquiry path) and, when SERVICES_INQUIRY_EMAIL is set,
    emails it. A 'type' field distinguishes support / sales / general so one
    backend can serve all three cards.
    """
    submitted = False
    errors: dict[str, str] = {}
    form = {"name": "", "email": "", "type": "support", "request": ""}

    if request.method == "POST":
        form = {
            "name": (request.POST.get("name") or "").strip(),
            "email": (request.POST.get("email") or "").strip(),
            "type": (request.POST.get("type") or "support").strip(),
            "request": (request.POST.get("request") or "").strip(),
        }
        if not form["name"]:
            errors["name"] = "お名前をご記入ください。"
        if not form["request"]:
            errors["request"] = "ご相談内容をご記入ください。"
        if not errors:
            from ..models import ServiceInquiry

            inquiry = ServiceInquiry.objects.create(
                name=form["name"][:120],
                affiliation=form["email"][:200],
                request=f"[{form['type']}] {form['request']}",
                budget=form["type"][:120],
            )
            _notify_contact_inquiry(inquiry, form)
            submitted = True
            form = {"name": "", "email": "", "type": "support", "request": ""}

    return render(
        request,
        "public_app/legal/contact.html",
        {"submitted": submitted, "errors": errors, "form": form},
    )


def _notify_contact_inquiry(inquiry, form):
    """Best-effort email of a contact-form inquiry. DB is the record of truth."""
    from django.conf import settings

    to_addr = (getattr(settings, "SERVICES_INQUIRY_EMAIL", "") or "").strip()
    if not to_addr:
        return
    from django.core.mail import send_mail

    subject = f"[SciTeX contact] {form.get('type', 'general')}: {inquiry.name}"
    body = (
        f"お名前: {inquiry.name}\n"
        f"ご連絡先: {form.get('email') or '-'}\n"
        f"種別: {form.get('type')}\n"
        f"受付日時: {inquiry.created_at:%Y-%m-%d %H:%M}\n\n"
        f"ご相談内容:\n{inquiry.request}\n"
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to_addr],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning(
            "ContactInquiry %s stored but email to %s failed",
            inquiry.pk,
            to_addr,
            exc_info=True,
        )


def privacy_policy(request):
    """Privacy policy page."""
    return render(request, "public_app/legal/privacy_policy.html")


def terms_of_use(request):
    """Terms of use page."""
    return render(request, "public_app/legal/terms_of_use.html")


def cookie_policy(request):
    """Cookie policy page."""
    return render(request, "public_app/legal/cookie_policy.html")


def tokushoho(request):
    """特定商取引法に基づく表記 (Specified Commercial Transactions Act).

    All values are config-driven (config/settings/settings_commerce.py,
    env keys SCITEX_HUB_COMPANY_*). Unfinalized values (public email)
    stay empty in the environment and the template renders an explicit
    準備中 notice — never a fake value.
    """
    context = {
        "company_name": settings.COMPANY_NAME,
        "company_representative": settings.COMPANY_REPRESENTATIVE,
        "company_address": settings.COMPANY_ADDRESS,
        "company_phone": settings.COMPANY_PHONE,
        "company_contact_email": settings.COMPANY_CONTACT_EMAIL,
        "billing_plans": settings.BILLING_PLANS,
        # Prices come from data/pricing.json, never from literals in the
        # template — test_pricing_ssot.py scans this app's templates and
        # views for hard-coded amounts. BILLING_PLANS stays empty on
        # purpose (checkout is shut); these are DISPLAY prices only, and
        # published_price_rows() already hides anything not yet for sale.
        #
        # This is a JAPANESE legal page (特定商取引法に基づく表記): it must
        # read in Japanese regardless of the site's English-default policy.
        # The override is entered BEFORE published_price_rows() so the
        # call-time gettext inside the pricing format layer bakes Japanese
        # strings into the context (they are rendered verbatim in the
        # template, not through {% trans %}).
    }
    with translation.override("ja"):
        rows = published_price_rows()
        # The yen reference is a DERIVED ARTIFACT (USD is the SSoT): fetch the
        # live rate and compute each row's yen from usd_amount × rate. The
        # rate + as-of date are shown on the page so the method is transparent.
        fx = get_usd_jpy_rate()
        annotate_jpy_reference(rows, fx["rate"])
        context["fx_rate"] = fx["rate"]
        # Display-ready values for the page note: rate to 1 decimal, and the
        # rate's as-of date in JST (a JP legal page, not UTC).
        context["fx_rate_display"] = f"{fx['rate']:.1f}" if fx["rate"] else None
        if fx["as_of"]:
            try:
                from datetime import datetime, timedelta, timezone

                jst = timezone(timedelta(hours=9))
                dt = datetime.strptime(fx["as_of"], "%a, %d %b %Y %H:%M:%S %z")
                context["fx_as_of_display"] = dt.astimezone(jst).strftime("%Y年%m月%d日")
            except ValueError:
                context["fx_as_of_display"] = fx["as_of"]
        else:
            context["fx_as_of_display"] = ""
        context["published_price_rows"] = rows
        return render(request, "public_app/legal/tokushoho.html", context)


# EOF
