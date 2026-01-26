#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Donation page view with payment processing.

Handles:
- Donation form submission
- Email verification
- Payment processing (Stripe, PayPal, GitHub)
- Funding progress tracking
"""

from __future__ import annotations

from django.contrib import messages
from django.db import models
from django.shortcuts import redirect, render
from django.utils import timezone


def donate(request):
    """Donate page view with payment processing."""
    from ..forms import DonationForm
    from ..models import Donation, DonationTier

    # Get donation tiers
    tiers = (
        DonationTier.objects.filter(is_active=True)
        if DonationTier.objects.exists()
        else []
    )

    if request.method == "POST":
        # Check if this is email verification request
        if "verify_email" in request.POST:
            return _handle_email_verification(request)

        # Process donation
        elif "process_donation" in request.POST:
            form = DonationForm(request.POST)
            if form.is_valid():
                return _process_donation(request, form)
    else:
        form = DonationForm()

    # Get recent public donations
    recent_donations = (
        Donation.objects.filter(
            is_public=True, is_visitor=False, status="completed"
        ).select_related("user")[:10]
        if Donation.objects.exists()
        else []
    )

    # Calculate funding progress
    current_year = timezone.now().year
    year_donations = (
        Donation.objects.filter(
            status="completed", created_at__year=current_year
        ).aggregate(total=models.Sum("amount"))["total"]
        or 0
        if Donation.objects.exists()
        else 0
    )

    funding_goal = 75000  # $75,000 annual goal
    funding_percentage = min(100, int((year_donations / funding_goal) * 100))

    context = {
        "form": form,
        "tiers": tiers,
        "recent_donations": recent_donations,
        "year_donations": year_donations,
        "funding_goal": funding_goal,
        "funding_percentage": funding_percentage,
    }

    return render(request, "public_app/pages/donate.html", context)


def _handle_email_verification(request):
    """Handle email verification request."""
    from ..forms import EmailVerificationForm

    email_form = EmailVerificationForm(request.POST)
    if email_form.is_valid():
        if email_form.send_verification_email():
            messages.success(request, "Verification code sent to your email!")
            request.session["verification_email"] = email_form.cleaned_data["email"]
            return redirect("cloud_app:verify-email")
        else:
            messages.error(
                request,
                "Failed to send verification email. Please try again.",
            )
    return redirect("cloud_app:donate")


def _process_donation(request, form):
    """Process a donation submission."""
    from .utils import send_donation_confirmation

    donation = form.save(commit=False)

    # If user is authenticated, link to user
    if request.user.is_authenticated:
        donation.user = request.user

    # Save donation as pending
    donation.save()

    # Process based on payment method
    if donation.payment_method == "credit_card":
        # Simulate Stripe payment
        transaction_id = (
            f"STRIPE_{donation.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )
        donation.complete_donation(transaction_id)
        messages.success(
            request,
            f"Thank you for your ${donation.amount} donation!",
        )

        # Send confirmation email
        send_donation_confirmation(donation)

        return redirect("cloud_app:donation-success", donation_id=donation.id)

    elif donation.payment_method == "paypal":
        # Redirect to PayPal
        messages.info(request, "Redirecting to PayPal...")
        return redirect("cloud_app:donate")  # Would redirect to PayPal in production

    elif donation.payment_method == "github":
        # Redirect to GitHub Sponsors
        return redirect("https://github.com/sponsors/SciTex-AI")

    return redirect("cloud_app:donate")


# EOF
