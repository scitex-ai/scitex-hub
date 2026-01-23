"""
Sustainability App Models

Models for donations, fundraising, and sustainability features.
Extracted from cloud_app to properly organize fundraising-related functionality.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Donation(models.Model):
    """Model for tracking donations."""

    PAYMENT_METHODS = [
        ("credit_card", "Credit Card"),
        ("paypal", "PayPal"),
        ("github", "GitHub Sponsors"),
        ("bank_transfer", "Bank Transfer"),
    ]

    DONATION_STATUS = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    # Donor information
    donor_name = models.CharField(max_length=255)
    donor_email = models.EmailField()
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations"
    )

    # Donation details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    # Status tracking
    status = models.CharField(max_length=20, choices=DONATION_STATUS, default="pending")
    transaction_id = models.CharField(max_length=255, blank=True)

    # Preferences
    is_public = models.BooleanField(
        default=False, help_text="Show donation publicly on supporters page"
    )
    is_visitor = models.BooleanField(
        default=False, help_text="Hide donor name if public"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Additional information
    message = models.TextField(blank=True, help_text="Optional message from donor")
    notes = models.TextField(blank=True, help_text="Internal notes")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.donor_name} - ${self.amount} ({self.status})"

    def complete_donation(self, transaction_id):
        """Mark donation as completed."""
        self.status = "completed"
        self.transaction_id = transaction_id
        self.completed_at = timezone.now()
        self.save()

    def get_display_name(self):
        """Get display name for public listing."""
        if self.is_visitor:
            return "Visitor"
        return self.donor_name


class DonationTier(models.Model):
    """Model for donation tiers and benefits."""

    name = models.CharField(
        max_length=100, help_text="Tier name (e.g., 'Bronze Supporter')"
    )
    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum donation amount for this tier",
    )
    description = models.TextField(help_text="Description of the tier")
    benefits = models.TextField(help_text="Benefits provided to donors in this tier")
    badge_color = models.CharField(
        max_length=7,
        default="#4a6baf",
        help_text="Hex color code for badge (e.g., #4a6baf)",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this tier is currently offered"
    )

    # Display order
    display_order = models.IntegerField(
        default=0, help_text="Order for displaying tiers"
    )

    class Meta:
        ordering = ["display_order", "minimum_amount"]
        verbose_name = "Donation Tier"
        verbose_name_plural = "Donation Tiers"

    def __str__(self):
        return f"{self.name} (${self.minimum_amount}+)"

    def get_donor_count(self):
        """Get count of donors in this tier."""
        return Donation.objects.filter(
            status="completed", amount__gte=self.minimum_amount
        ).count()
