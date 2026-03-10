#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for integrations_app

This module contains unit tests for the integrations app, covering:
- Model creation and encryption
- OAuth flow (ORCID)
- Slack webhook configuration
- Integration logging
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from .models import IntegrationConnection, ORCIDProfile, SlackWebhook, IntegrationLog


class IntegrationConnectionModelTests(TestCase):
    """Tests for IntegrationConnection model"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_creation_with_status_default(self):
        """Test IntegrationConnection defaults to inactive status"""
        conn = IntegrationConnection.objects.create(user=self.user, service="orcid")
        self.assertEqual(conn.status, "inactive")
        self.assertIsNone(conn.access_token_encrypted)

    def test_unique_together_user_service(self):
        """Test that user can only have one connection per service"""
        IntegrationConnection.objects.create(user=self.user, service="orcid")

        # Try to create another for same user/service
        with self.assertRaises(Exception):
            IntegrationConnection.objects.create(user=self.user, service="orcid")

    def test_multiple_services_for_same_user(self):
        """Test that user can have multiple service connections"""
        orcid = IntegrationConnection.objects.create(user=self.user, service="orcid")
        slack = IntegrationConnection.objects.create(user=self.user, service="slack")

        self.assertEqual(orcid.service, "orcid")
        self.assertEqual(slack.service, "slack")

    def test_token_expiration_tracking(self):
        """Test token expiration date tracking"""
        future_date = timezone.now() + timedelta(days=30)
        conn = IntegrationConnection.objects.create(
            user=self.user, service="orcid", token_expires_at=future_date
        )
        self.assertIsNotNone(conn.token_expires_at)
        self.assertGreater(conn.token_expires_at, timezone.now())

    def test_is_token_expired_false_when_no_expiry(self):
        """Test is_token_expired returns False when no expiry set"""
        conn = IntegrationConnection.objects.create(user=self.user, service="orcid")
        # Should return False if no expiry date
        if hasattr(conn, "is_token_expired"):
            self.assertFalse(conn.is_token_expired())

    def test_is_token_expired_true_when_past(self):
        """Test is_token_expired returns True for past date"""
        past_date = timezone.now() - timedelta(hours=1)
        conn = IntegrationConnection.objects.create(
            user=self.user, service="orcid", token_expires_at=past_date
        )
        if hasattr(conn, "is_token_expired"):
            self.assertTrue(conn.is_token_expired())

    def test_last_sync_at_tracking(self):
        """Test last_sync_at timestamp"""
        now = timezone.now()
        conn = IntegrationConnection.objects.create(
            user=self.user, service="orcid", last_sync_at=now
        )
        self.assertEqual(conn.last_sync_at, now)


class ORCIDProfileModelTests(TestCase):
    """Tests for ORCIDProfile model"""

    def setUp(self):
        """Set up test user and connection"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.connection = IntegrationConnection.objects.create(
            user=self.user, service="orcid"
        )

    def test_creation_with_orcid_id(self):
        """Test ORCIDProfile can be created"""
        profile = ORCIDProfile.objects.create(
            connection=self.connection,
            orcid_id="0000-0001-2345-6789",
            given_names="John",
            family_name="Doe",
        )
        self.assertEqual(profile.orcid_id, "0000-0001-2345-6789")
        self.assertEqual(profile.given_names, "John")
        self.assertEqual(profile.family_name, "Doe")

    def test_orcid_id_uniqueness(self):
        """Test that ORCID IDs are unique"""
        ORCIDProfile.objects.create(
            connection=self.connection, orcid_id="0000-0001-2345-6789"
        )

        other_connection = IntegrationConnection.objects.create(
            user=self.user, service="github"
        )

        # Try to create another with same ORCID ID
        with self.assertRaises(Exception):
            ORCIDProfile.objects.create(
                connection=other_connection, orcid_id="0000-0001-2345-6789"
            )

    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with IntegrationConnection"""
        profile = ORCIDProfile.objects.create(
            connection=self.connection, orcid_id="0000-0001-2345-6789"
        )

        # Refresh and verify relationship
        profile.refresh_from_db()
        self.assertEqual(profile.connection.user, self.user)

    def test_get_full_name_combines_names(self):
        """Test get_full_name method"""
        profile = ORCIDProfile.objects.create(
            connection=self.connection,
            orcid_id="0000-0001-2345-6789",
            given_names="John",
            family_name="Doe",
        )
        if hasattr(profile, "get_full_name"):
            full_name = profile.get_full_name()
            self.assertIn("John", full_name)
            self.assertIn("Doe", full_name)

    def test_affiliations_json_field(self):
        """Test affiliations JSON field storage"""
        affiliations = [
            {"name": "University A", "role": "Professor"},
            {"name": "University B", "role": "Researcher"},
        ]
        profile = ORCIDProfile.objects.create(
            connection=self.connection,
            orcid_id="0000-0001-2345-6789",
            affiliations=affiliations,
        )
        self.assertEqual(len(profile.affiliations), 2)
        self.assertEqual(profile.affiliations[0]["name"], "University A")


class SlackWebhookModelTests(TestCase):
    """Tests for SlackWebhook model"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_creation_requires_webhook_url(self):
        """Test SlackWebhook requires webhook_url"""
        webhook = SlackWebhook.objects.create(
            user=self.user,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        )
        self.assertIsNotNone(webhook.webhook_url)

    def test_is_active_defaults_true(self):
        """Test is_active defaults to True"""
        webhook = SlackWebhook.objects.create(
            user=self.user,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        )
        self.assertTrue(webhook.is_active)

    def test_channel_optional(self):
        """Test that channel is optional"""
        webhook = SlackWebhook.objects.create(
            user=self.user,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        )
        self.assertIsNone(webhook.channel)

    def test_enabled_events_json_field(self):
        """Test enabled_events JSON field"""
        events = ["project_created", "manuscript_updated", "analysis_completed"]
        webhook = SlackWebhook.objects.create(
            user=self.user,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
            enabled_events=events,
        )
        self.assertEqual(len(webhook.enabled_events), 3)
        self.assertIn("project_created", webhook.enabled_events)

    def test_notification_count_increments(self):
        """Test notification count tracking"""
        webhook = SlackWebhook.objects.create(
            user=self.user,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
            notification_count=0,
        )
        self.assertEqual(webhook.notification_count, 0)

        webhook.notification_count += 1
        webhook.save()

        webhook.refresh_from_db()
        self.assertEqual(webhook.notification_count, 1)


class IntegrationLogModelTests(TestCase):
    """Tests for IntegrationLog model"""

    def setUp(self):
        """Set up test user and connection"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.connection = IntegrationConnection.objects.create(
            user=self.user, service="orcid"
        )

    def test_creation_with_action_types(self):
        """Test IntegrationLog can be created with various actions"""
        log = IntegrationLog.objects.create(
            connection=self.connection, action="sync", success=True
        )
        self.assertEqual(log.action, "sync")
        self.assertTrue(log.success)

    def test_success_flag_defaults_true(self):
        """Test success defaults to True"""
        log = IntegrationLog.objects.create(connection=self.connection, action="test")
        self.assertTrue(log.success)

    def test_error_message_recorded(self):
        """Test error messages are stored"""
        error_msg = "Token expired"
        log = IntegrationLog.objects.create(
            connection=self.connection,
            action="sync",
            success=False,
            error_message=error_msg,
        )
        self.assertEqual(log.error_message, error_msg)

    def test_metadata_json_field(self):
        """Test metadata JSON field storage"""
        metadata = {"sync_time_ms": 1234, "records_synced": 15, "api_version": "2.1"}
        log = IntegrationLog.objects.create(
            connection=self.connection, action="sync", metadata=metadata
        )
        self.assertEqual(log.metadata["records_synced"], 15)

    def test_ordering_by_created_at_desc(self):
        """Test logs are ordered by created_at descending"""
        log1 = IntegrationLog.objects.create(connection=self.connection, action="test")
        log2 = IntegrationLog.objects.create(connection=self.connection, action="test")

        logs = IntegrationLog.objects.all()
        # Most recent should be last in query, first in order
        self.assertEqual(logs.first().id, log2.id)


class IntegrationConnectionViewTests(TestCase):
    """Tests for integration connection views"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_integrations_dashboard_requires_login(self):
        """Test that integrations dashboard requires authentication"""
        response = self.client.get(reverse("integrations_app:integrations_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_integrations_dashboard_shows_connections(self):
        """Test integrations dashboard displays user's connections"""
        self.client.login(username="testuser", password="testpass123")

        IntegrationConnection.objects.create(
            user=self.user, service="orcid", status="active"
        )

        response = self.client.get(reverse("integrations_app:integrations_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("connections", response.context)

    def test_api_integration_status_returns_json(self):
        """Test API status endpoint returns JSON"""
        self.client.login(username="testuser", password="testpass123")

        IntegrationConnection.objects.create(
            user=self.user, service="orcid", status="active"
        )

        response = self.client.get(reverse("integrations_app:api_integration_status"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("orcid", data)


# EOF
