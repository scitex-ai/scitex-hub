#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/utils.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/utils.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Utility Views

Helper views and shared functionality.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

logger = logging.getLogger("scitex")


def demo(request):
    """Demo page."""
    return render(request, "public_app/demo.html")


def donation_success(request, donation_id):
    """Donation success page."""
    from ..models import Donation

    try:
        donation = Donation.objects.get(id=donation_id)
        if (
            donation.donor_email != request.session.get("verified_email")
            and not request.user.is_authenticated
        ):
            raise PermissionDenied
    except Donation.DoesNotExist:
        messages.error(request, "Donation not found.")
        return redirect("cloud_app:donate")

    context = {
        "donation": donation,
    }

    return render(request, "public_app/donation_success.html", context)


def send_donation_confirmation(donation):
    """Send donation confirmation email."""
    from django.core.mail import send_mail

    subject = "Thank you for supporting SciTeX!"

    message = f"""
Dear {donation.donor_name},

Thank you for your generous ${donation.amount} donation to SciTeX!

Your support helps us maintain and improve our open-source scientific research platform,
making advanced tools accessible to researchers worldwide.

Transaction Details:
- Amount: ${donation.amount} USD
- Payment Method: {donation.get_payment_method_display()}
- Transaction ID: {donation.transaction_id}
- Date: {donation.completed_at.strftime("%B %d, %Y")}

This email serves as your donation receipt for tax purposes.

If you have any questions, please contact us at support@scitex.ai.

With gratitude,
The SciTeX Team
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [donation.donor_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send donation confirmation: {str(e)}")


# EOF
