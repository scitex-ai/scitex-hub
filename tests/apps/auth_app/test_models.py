#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/auth_app/models.py"""

import pytest

# from apps.auth_app.models import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/auth_app/models.py
# --------------------------------------------------------------------------------
# from django.db import models
# from django.contrib.auth.models import User
# import random
# import string
# from datetime import timedelta
# from django.utils import timezone
# 
# 
# # Japanese Academic domains to recognize
# JAPANESE_ACADEMIC_DOMAINS = [
#     # Japanese Academic (.ac.jp) - All academic institutions
#     ".ac.jp",
#     ".u-tokyo.ac.jp",
#     ".kyoto-u.ac.jp",
#     ".osaka-u.ac.jp",
#     ".tohoku.ac.jp",
#     ".nagoya-u.ac.jp",
#     ".kyushu-u.ac.jp",
#     ".hokudai.ac.jp",
#     ".tsukuba.ac.jp",
#     ".hiroshima-u.ac.jp",
#     ".kobe-u.ac.jp",
#     ".waseda.jp",
#     ".keio.ac.jp",
#     # Government Research Institutions (.go.jp)
#     ".go.jp",  # Broader government research support
#     ".riken.jp",
#     ".aist.go.jp",
#     ".nict.go.jp",
#     ".jaxa.jp",
#     ".jst.go.jp",
#     ".nims.go.jp",
#     ".nies.go.jp",
# ]
# 
# 
# def is_japanese_academic_email(email):
#     """Check if email belongs to Japanese academic institution"""
#     if not email:
#         return False
#     try:
#         domain = email.lower().split("@")[1]
#         # Check if domain matches exactly or ends with the academic domain
#         for academic_domain in JAPANESE_ACADEMIC_DOMAINS:
#             # Remove leading dot for exact matching
#             clean_domain = academic_domain.lstrip(".")
#             if domain == clean_domain or domain.endswith(academic_domain):
#                 return True
#         return False
#     except (IndexError, AttributeError):
#         return False
# 
# 
# class UserProfile(models.Model):
#     """Extended user profile for SciTeX users"""
# 
#     PROFESSION_CHOICES = [
#         ("student", "Student (Undergraduate/Graduate)"),
#         ("researcher", "Researcher/Postdoc"),
#         ("professor", "Professor/Faculty"),
#         ("industry", "Industry Professional"),
#         ("independent", "Independent Researcher"),
#         ("other", "Other"),
#     ]
# 
#     RESEARCH_FIELD_CHOICES = [
#         ("computer_science", "Computer Science"),
#         ("biology", "Biology & Life Sciences"),
#         ("physics", "Physics"),
#         ("chemistry", "Chemistry"),
#         ("mathematics", "Mathematics"),
#         ("engineering", "Engineering"),
#         ("medicine", "Medicine & Health"),
#         ("social_sciences", "Social Sciences"),
#         ("humanities", "Humanities"),
#         ("earth_sciences", "Earth Sciences"),
#         ("psychology", "Psychology"),
#         ("neuroscience", "Neuroscience"),
#         ("other", "Other"),
#     ]
# 
#     user = models.OneToOneField(
#         User, on_delete=models.CASCADE, related_name="auth_profile"
#     )
#     profession = models.CharField(max_length=20, choices=PROFESSION_CHOICES, blank=True)
#     research_field = models.CharField(
#         max_length=20, choices=RESEARCH_FIELD_CHOICES, blank=True
#     )
#     institution = models.CharField(max_length=200, blank=True)
#     bio = models.TextField(max_length=500, blank=True)
# 
#     # Academic verification
#     is_academic_verified = models.BooleanField(
#         default=False, help_text="Email verified as academic institution"
#     )
# 
#     # Preferences
#     email_notifications = models.BooleanField(default=True)
#     weekly_digest = models.BooleanField(default=True)
# 
#     # Theme preferences
#     theme_preference = models.CharField(
#         max_length=10,
#         choices=[("light", "Light"), ("dark", "Dark")],
#         default="dark",
#         help_text="Site theme preference (light/dark)",
#     )
#     code_theme_light = models.CharField(
#         max_length=50,
#         default="atom-one-light",
#         help_text="Code highlighting theme for light mode",
#     )
#     code_theme_dark = models.CharField(
#         max_length=50, default="nord", help_text="Code highlighting theme for dark mode"
#     )
# 
#     # Editor (CodeMirror) theme preferences for writer app
#     editor_theme_light = models.CharField(
#         max_length=50,
#         default="neat",
#         help_text="Editor theme for light mode (CodeMirror)",
#     )
#     editor_theme_dark = models.CharField(
#         max_length=50,
#         default="nord",
#         help_text="Editor theme for dark mode (CodeMirror)",
#     )
# 
#     # Profile completion tracking
#     profile_completed = models.BooleanField(default=False)
#     profile_completion_date = models.DateTimeField(null=True, blank=True)
# 
#     # Activity tracking
#     last_login_at = models.DateTimeField(null=True, blank=True)
#     total_login_count = models.IntegerField(default=0)
# 
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
# 
#     class Meta:
#         verbose_name = "User Profile"
#         verbose_name_plural = "User Profiles"
# 
#     def __str__(self):
#         return f"{self.user.username} Profile"
# 
#     def save(self, *args, **kwargs):
#         # Check academic email verification
#         if self.user.email:
#             self.is_academic_verified = is_japanese_academic_email(self.user.email)
# 
#         # Check profile completion
#         required_fields = [self.profession, self.research_field, self.institution]
#         if all(required_fields) and not self.profile_completed:
#             self.profile_completed = True
#             self.profile_completion_date = timezone.now()
# 
#         super().save(*args, **kwargs)
# 
#     def get_completion_percentage(self):
#         """Calculate profile completion percentage"""
#         fields = [
#             self.user.first_name,
#             self.user.last_name,
#             self.profession,
#             self.research_field,
#             self.institution,
#             self.bio,
#         ]
#         completed = sum(1 for field in fields if field)
#         return int((completed / len(fields)) * 100)
# 
# 
# class EmailVerification(models.Model):
#     """Email verification for user registration"""
# 
#     user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="auth_email_verifications"
#     )
#     email = models.EmailField()
#     code = models.CharField(max_length=6)
#     created_at = models.DateTimeField(auto_now_add=True)
#     verified_at = models.DateTimeField(null=True, blank=True)
#     expires_at = models.DateTimeField()
#     is_verified = models.BooleanField(default=False)
# 
#     class Meta:
#         verbose_name = "Email Verification"
#         verbose_name_plural = "Email Verifications"
#         ordering = ["-created_at"]
# 
#     def __str__(self):
#         return f"{self.email} - {self.code}"
# 
#     def save(self, *args, **kwargs):
#         if not self.console:
#             self.code = self.generate_code()
#         if not self.expires_at:
#             self.expires_at = timezone.now() + timedelta(minutes=10)
#         super().save(*args, **kwargs)
# 
#     @staticmethod
#     def generate_code():
#         """Generate a 6-digit verification code"""
#         return "".join(random.choices(string.digits, k=6))
# 
#     def is_expired(self):
#         """Check if verification code has expired"""
#         return timezone.now() > self.expires_at
# 
#     def verify(self):
#         """Mark verification as completed"""
#         self.is_verified = True
#         self.verified_at = timezone.now()
#         self.save()
# 
# 
# # Signal handlers for automatic profile creation and Gitea sync
# class AuthenticatedDevice(models.Model):
#     """
#     Tracks which users have authenticated on a specific device/browser.
#     Enables multi-account switching like Google/GitHub.
#     """
# 
#     device_id = models.CharField(
#         max_length=64,
#         unique=True,
#         db_index=True,
#         help_text="Unique identifier for this browser/device",
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_used = models.DateTimeField(auto_now=True)
# 
#     class Meta:
#         ordering = ["-last_used"]
# 
#     def __str__(self):
#         return f"Device {self.device_id[:8]}..."
# 
# 
# class DeviceAccount(models.Model):
#     """
#     Links a user account to a device.
#     Allows switching between accounts authenticated on same device.
#     """
# 
#     device = models.ForeignKey(
#         AuthenticatedDevice, on_delete=models.CASCADE, related_name="accounts"
#     )
#     user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="authenticated_devices"
#     )
#     authenticated_at = models.DateTimeField(auto_now_add=True)
#     last_used = models.DateTimeField(auto_now=True)
# 
#     class Meta:
#         unique_together = ("device", "user")
#         ordering = ["-last_used"]
# 
#     def __str__(self):
#         return f"{self.user.username} on device {self.device.device_id[:8]}..."
# 
# 
# from django.db.models.signals import post_save, pre_delete
# from django.dispatch import receiver
# import logging
# 
# logger = logging.getLogger(__name__)
# 
# 
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     """Automatically create UserProfile when User is created"""
#     if created:
#         UserProfile.objects.create(user=instance)
# 
# 
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     """Save UserProfile when User is saved"""
#     if hasattr(instance, "auth_profile"):
#         instance.auth_profile.save()
# 
# 
# @receiver(pre_delete, sender=User)
# def delete_gitea_user(sender, instance, **kwargs):
#     """Delete corresponding Gitea user when Django user is deleted"""
#     try:
#         from apps.gitea_app.api_client import GiteaClient, GiteaAPIError
# 
#         client = GiteaClient()
#         client.delete_user(instance.username)
#         logger.info(f"Deleted Gitea user: {instance.username}")
#     except GiteaAPIError as e:
#         logger.warning(f"Failed to delete Gitea user {instance.username}: {e}")
#     except Exception as e:
#         logger.error(f"Error deleting Gitea user {instance.username}: {e}")

# --------------------------------------------------------------------------------
# End of Source Code from: apps/auth_app/models.py
# --------------------------------------------------------------------------------
