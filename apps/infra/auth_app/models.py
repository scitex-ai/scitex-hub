import random
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# Account-linking tables (scitex.ai identity: one verified address -> one
# human -> many provider identities). They live in their own package next to
# the logic that uses them; re-exported here because Django's app registry
# only auto-imports ``<app>.models``, and an unimported model is an
# unmigrated one. See apps/infra/auth_app/account_linking/models.py.
from apps.infra.auth_app.account_linking.models import (  # noqa: F401
    LinkedIdentity,
    VerifiedEmail,
)

# Japanese Academic domains to recognize
JAPANESE_ACADEMIC_DOMAINS = [
    # Japanese Academic (.ac.jp) - All academic institutions
    ".ac.jp",
    ".u-tokyo.ac.jp",
    ".kyoto-u.ac.jp",
    ".osaka-u.ac.jp",
    ".tohoku.ac.jp",
    ".nagoya-u.ac.jp",
    ".kyushu-u.ac.jp",
    ".hokudai.ac.jp",
    ".tsukuba.ac.jp",
    ".hiroshima-u.ac.jp",
    ".kobe-u.ac.jp",
    ".waseda.jp",
    ".keio.ac.jp",
    # Government Research Institutions (.go.jp)
    ".go.jp",  # Broader government research support
    ".riken.jp",
    ".aist.go.jp",
    ".nict.go.jp",
    ".jaxa.jp",
    ".jst.go.jp",
    ".nims.go.jp",
    ".nies.go.jp",
]


def is_japanese_academic_email(email):
    """Check if email belongs to Japanese academic institution"""
    if not email:
        return False
    try:
        domain = email.lower().split("@")[1]
        # Check if domain matches exactly or ends with the academic domain
        for academic_domain in JAPANESE_ACADEMIC_DOMAINS:
            # Remove leading dot for exact matching
            clean_domain = academic_domain.lstrip(".")
            if domain == clean_domain or domain.endswith(academic_domain):
                return True
        return False
    except (IndexError, AttributeError):
        return False


class UserProfile(models.Model):
    """Extended user profile for SciTeX users"""

    PROFESSION_CHOICES = [
        ("student", "Student (Undergraduate/Graduate)"),
        ("researcher", "Researcher/Postdoc"),
        ("professor", "Professor/Faculty"),
        ("industry", "Industry Professional"),
        ("independent", "Independent Researcher"),
        ("other", "Other"),
    ]

    RESEARCH_FIELD_CHOICES = [
        ("computer_science", "Computer Science"),
        ("biology", "Biology & Life Sciences"),
        ("physics", "Physics"),
        ("chemistry", "Chemistry"),
        ("mathematics", "Mathematics"),
        ("engineering", "Engineering"),
        ("medicine", "Medicine & Health"),
        ("social_sciences", "Social Sciences"),
        ("humanities", "Humanities"),
        ("earth_sciences", "Earth Sciences"),
        ("psychology", "Psychology"),
        ("neuroscience", "Neuroscience"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="auth_profile"
    )
    profession = models.CharField(max_length=20, choices=PROFESSION_CHOICES, blank=True)
    research_field = models.CharField(
        max_length=20, choices=RESEARCH_FIELD_CHOICES, blank=True
    )
    institution = models.CharField(max_length=200, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    # Academic verification
    is_academic_verified = models.BooleanField(
        default=False, help_text="Email verified as academic institution"
    )

    # Preferences
    email_notifications = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=True)

    # Theme preferences
    theme_preference = models.CharField(
        max_length=10,
        choices=[("light", "Light"), ("dark", "Dark")],
        default="dark",
        help_text="Site theme preference (light/dark)",
    )
    code_theme_light = models.CharField(
        max_length=50,
        default="atom-one-light",
        help_text="Code highlighting theme for light mode",
    )
    code_theme_dark = models.CharField(
        max_length=50, default="nord", help_text="Code highlighting theme for dark mode"
    )

    # Editor (CodeMirror) theme preferences for writer app
    editor_theme_light = models.CharField(
        max_length=50,
        default="neat",
        help_text="Editor theme for light mode (CodeMirror)",
    )
    editor_theme_dark = models.CharField(
        max_length=50,
        default="nord",
        help_text="Editor theme for dark mode (CodeMirror)",
    )

    # Profile completion tracking
    profile_completed = models.BooleanField(default=False)
    profile_completion_date = models.DateTimeField(null=True, blank=True)

    # Activity tracking
    last_login_at = models.DateTimeField(null=True, blank=True)
    total_login_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        # Check academic email verification
        if self.user.email:
            self.is_academic_verified = is_japanese_academic_email(self.user.email)

        # Check profile completion
        required_fields = [self.profession, self.research_field, self.institution]
        if all(required_fields) and not self.profile_completed:
            self.profile_completed = True
            self.profile_completion_date = timezone.now()

        super().save(*args, **kwargs)

    def get_completion_percentage(self):
        """Calculate profile completion percentage"""
        fields = [
            self.user.first_name,
            self.user.last_name,
            self.profession,
            self.research_field,
            self.institution,
            self.bio,
        ]
        completed = sum(1 for field in fields if field)
        return int((completed / len(fields)) * 100)


class EmailVerification(models.Model):
    """Email verification for user registration"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="auth_email_verifications"
    )
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        """Generate a 6-digit verification code"""
        return "".join(random.choices(string.digits, k=6))

    def is_expired(self):
        """Check if verification code has expired"""
        return timezone.now() > self.expires_at

    def verify(self):
        """Mark verification as completed"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()


# Signal handlers for automatic profile creation and Gitea sync
class AuthenticatedDevice(models.Model):
    """
    Tracks which users have authenticated on a specific device/browser.
    Enables multi-account switching like Google/GitHub.
    """

    device_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique identifier for this browser/device",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_used"]

    def __str__(self):
        return f"Device {self.device_id[:8]}..."


class DeviceAccount(models.Model):
    """
    Links a user account to a device.
    Allows switching between accounts authenticated on same device.
    """

    device = models.ForeignKey(
        AuthenticatedDevice, on_delete=models.CASCADE, related_name="accounts"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="authenticated_devices"
    )
    authenticated_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("device", "user")
        ordering = ["-last_used"]

    def __str__(self):
        return f"{self.user.username} on device {self.device.device_id[:8]}..."


class LoginHistory(models.Model):
    """
    Tracks all user login events for security auditing.
    Stores who logged in, when, from where, and with what device.
    """

    LOGIN_METHOD_CHOICES = [
        ("email", "Email/Password"),
        ("google", "Google OAuth"),
        ("github", "GitHub OAuth"),
        ("visitor", "Visitor Account"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="login_history"
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text="Browser/device info")
    login_method = models.CharField(
        max_length=20, choices=LOGIN_METHOD_CHOICES, default="email"
    )
    success = models.BooleanField(default=True, help_text="Whether login succeeded")
    failure_reason = models.CharField(
        max_length=100, blank=True, help_text="Reason if login failed"
    )

    class Meta:
        verbose_name = "Login History"
        verbose_name_plural = "Login Histories"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.user.username} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def log_login(cls, user, request, method="email", success=True, failure_reason=""):
        """
        Convenience method to log a login event.

        Usage:
            LoginHistory.log_login(user, request, method='email')
        """
        # Get IP address (handle proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")

        # Get user agent
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]  # Limit length

        return cls.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            login_method=method,
            success=success,
            failure_reason=failure_reason,
        )


import logging

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, "auth_profile"):
        instance.auth_profile.save()


@receiver(pre_delete, sender=User)
def delete_gitea_user(sender, instance, **kwargs):
    """Delete corresponding Gitea user when Django user is deleted"""
    try:
        from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

        client = GiteaClient()
        client.delete_user(instance.username)
        logger.info(f"Deleted Gitea user: {instance.username}")
    except GiteaAPIError as e:
        logger.warning(f"Failed to delete Gitea user {instance.username}: {e}")
    except Exception as e:
        logger.error(f"Error deleting Gitea user {instance.username}: {e}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Automatically log when a user logs in"""
    try:
        # Determine login method
        method = "email"  # Default
        if hasattr(request, "session"):
            # Check if this was a social login
            sociallogin = request.session.get("socialaccount_sociallogin")
            if sociallogin:
                provider = sociallogin.get("account", {}).get("provider", "")
                if provider in ["google", "github"]:
                    method = provider

        # Check if visitor account
        if user.username.startswith("visitor-"):
            method = "visitor"

        LoginHistory.log_login(user, request, method=method)

        # Also update UserProfile login tracking
        if hasattr(user, "auth_profile"):
            user.auth_profile.last_login_at = timezone.now()
            user.auth_profile.total_login_count += 1
            user.auth_profile.save(update_fields=["last_login_at", "total_login_count"])

        logger.info(f"Login recorded: {user.username} via {method}")
    except Exception as e:
        logger.error(f"Failed to log login for {user.username}: {e}")
