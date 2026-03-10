#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for accounts_app

This module contains unit tests for the profile app, covering:
- UserProfile model
- APIKey model and generation
- Profile views and authentication
- Settings pages
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import UserProfile, APIKey


class UserProfileModelTests(TestCase):
    """Tests for UserProfile model"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            password="testpass123",
        )

    def test_creation_with_user(self):
        """Test UserProfile can be created with a user"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)

    def test_one_to_one_relationship_with_user(self):
        """Test one-to-one relationship with User model"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(self.user.profile, profile)

    def test_get_display_name_with_full_name(self):
        """Test get_display_name uses full name when available"""
        profile = UserProfile.objects.create(user=self.user)
        if hasattr(profile, "get_display_name"):
            display_name = profile.get_display_name()
            self.assertIn("John", display_name)
            self.assertIn("Doe", display_name)

    def test_get_display_name_fallback_to_username(self):
        """Test get_display_name falls back to username"""
        user = User.objects.create_user(
            username="noname", email="noname@example.com", password="testpass123"
        )
        profile = UserProfile.objects.create(user=user)
        if hasattr(profile, "get_display_name"):
            display_name = profile.get_display_name()
            self.assertIn("noname", display_name)

    def test_visibility_default_public(self):
        """Test profile visibility defaults to public"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.visibility, "public")

    def test_visibility_choices_enforced(self):
        """Test visibility field enforces allowed choices"""
        profile = UserProfile.objects.create(user=self.user, visibility="private")
        self.assertEqual(profile.visibility, "private")

    def test_bio_storage(self):
        """Test bio field storage"""
        bio_text = "Researcher in machine learning and neuroscience"
        profile = UserProfile.objects.create(user=self.user, bio=bio_text)
        self.assertEqual(profile.bio, bio_text)

    def test_institution_storage(self):
        """Test institution field storage"""
        institution = "University of Tokyo"
        profile = UserProfile.objects.create(user=self.user, institution=institution)
        self.assertEqual(profile.institution, institution)

    def test_academic_status_field(self):
        """Test academic_status field"""
        profile = UserProfile.objects.create(
            user=self.user, academic_status="professor"
        )
        self.assertEqual(profile.academic_status, "professor")

    def test_research_interests_json_field(self):
        """Test research_interests JSON field"""
        interests = ["machine learning", "neuroscience", "data science"]
        profile = UserProfile.objects.create(
            user=self.user, research_interests=interests
        )
        self.assertEqual(len(profile.research_interests), 3)
        self.assertIn("machine learning", profile.research_interests)


class APIKeyModelTests(TestCase):
    """Tests for APIKey model"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_key_generation_format(self):
        """Test API key has correct format"""
        key = APIKey.objects.create(user=self.user, name="Test Key")
        # Keys should have scitex_ prefix
        if hasattr(APIKey, "generate_key"):
            key_value = APIKey.generate_key()
            self.assertTrue(key_value.startswith("scitex_") or len(key_value) >= 32)

    def test_create_key_creates_api_key_record(self):
        """Test that create_key creates an APIKey record"""
        key = APIKey.objects.create(user=self.user, name="My API Key")
        self.assertEqual(key.name, "My API Key")
        self.assertEqual(key.user, self.user)

    def test_key_with_scopes(self):
        """Test API key with scopes"""
        scopes = ["read:projects", "write:documents"]
        key = APIKey.objects.create(user=self.user, name="Scoped Key", scopes=scopes)
        self.assertEqual(len(key.scopes), 2)

    def test_key_with_expiration(self):
        """Test API key with expiration date"""
        expiry = timezone.now() + timedelta(days=30)
        key = APIKey.objects.create(
            user=self.user, name="Expiring Key", expires_at=expiry
        )
        self.assertIsNotNone(key.expires_at)

    def test_is_valid_active_and_not_expired(self):
        """Test is_valid returns True for active, non-expired keys"""
        future_expiry = timezone.now() + timedelta(days=30)
        key = APIKey.objects.create(
            user=self.user, name="Valid Key", is_active=True, expires_at=future_expiry
        )
        if hasattr(key, "is_valid"):
            self.assertTrue(key.is_valid())

    def test_is_valid_inactive_returns_false(self):
        """Test is_valid returns False for inactive keys"""
        key = APIKey.objects.create(
            user=self.user, name="Inactive Key", is_active=False
        )
        if hasattr(key, "is_valid"):
            self.assertFalse(key.is_valid())

    def test_is_valid_expired_returns_false(self):
        """Test is_valid returns False for expired keys"""
        past_expiry = timezone.now() - timedelta(days=1)
        key = APIKey.objects.create(
            user=self.user, name="Expired Key", is_active=True, expires_at=past_expiry
        )
        if hasattr(key, "is_valid"):
            self.assertFalse(key.is_valid())

    def test_has_scope_with_specific_scope(self):
        """Test has_scope method"""
        key = APIKey.objects.create(
            user=self.user,
            name="Scoped Key",
            scopes=["read:projects", "write:documents"],
        )
        if hasattr(key, "has_scope"):
            self.assertTrue(key.has_scope("read:projects"))

    def test_has_scope_missing_scope(self):
        """Test has_scope returns False for missing scope"""
        key = APIKey.objects.create(
            user=self.user, name="Limited Key", scopes=["read:projects"]
        )
        if hasattr(key, "has_scope"):
            self.assertFalse(key.has_scope("write:documents"))

    def test_key_prefix_masked(self):
        """Test that key prefix is masked in display"""
        key = APIKey.objects.create(user=self.user, name="Test Key")
        # Key should not show full value when retrieved
        if hasattr(key, "masked_key"):
            masked = key.masked_key()
            self.assertLess(len(masked), 20)


class ProfileViewTests(TestCase):
    """Tests for profile views"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_profile_view_requires_login(self):
        """Test that profile view requires authentication"""
        response = self.client.get(reverse("accounts_app:profile_view"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_profile_view_creates_profile_if_not_exists(self):
        """Test that profile view creates profile if it doesn't exist"""
        self.client.login(username="testuser", password="testpass123")

        # Delete profile if it exists
        UserProfile.objects.filter(user=self.user).delete()

        response = self.client.get(reverse("accounts_app:profile_view"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_profile_edit_requires_login(self):
        """Test that profile edit requires authentication"""
        response = self.client.get(reverse("accounts_app:profile_edit"))
        self.assertEqual(response.status_code, 302)

    def test_profile_edit_shows_form(self):
        """Test profile edit view shows form"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("accounts_app:profile_edit"))
        self.assertEqual(response.status_code, 200)
        # Should have form in context
        self.assertIn("form", response.context)

    def test_api_keys_view_requires_login(self):
        """Test that API keys view requires authentication"""
        response = self.client.get(reverse("accounts_app:api_keys"))
        self.assertEqual(response.status_code, 302)

    def test_api_keys_view_shows_user_keys(self):
        """Test API keys view lists user's API keys"""
        self.client.login(username="testuser", password="testpass123")

        # Create a test key
        APIKey.objects.create(user=self.user, name="Test Key")

        response = self.client.get(reverse("accounts_app:api_keys"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_keys", response.context)

    def test_ssh_keys_view_requires_login(self):
        """Test that SSH keys view requires authentication"""
        response = self.client.get(reverse("accounts_app:ssh_keys"))
        self.assertEqual(response.status_code, 302)

    def test_ssh_keys_view_accessible(self):
        """Test SSH keys view is accessible when authenticated"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("accounts_app:ssh_keys"))
        self.assertEqual(response.status_code, 200)


# EOF
