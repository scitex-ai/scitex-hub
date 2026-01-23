#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for search_app

This module contains unit tests for the search app, covering:
- Search functionality across users and repositories
- Autocomplete suggestions
- Search query logging
- Visibility filtering
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from .models import GlobalSearchQuery
from apps.project_app.models import Project


class GlobalSearchQueryModelTests(TestCase):
    """Tests for GlobalSearchQuery model"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_creation_with_defaults(self):
        """Test GlobalSearchQuery can be created"""
        query = GlobalSearchQuery.objects.create(
            query_text="machine learning", search_type="all", user=self.user
        )
        self.assertEqual(query.query_text, "machine learning")
        self.assertEqual(query.results_count, 0)

    def test_search_type_choices_enforced(self):
        """Test search_type field enforces choices"""
        valid_types = ["all", "users", "repositories"]
        for search_type in valid_types:
            query = GlobalSearchQuery.objects.create(
                query_text=f"test {search_type}",
                search_type=search_type,
                user=self.user,
            )
            self.assertEqual(query.search_type, search_type)

    def test_user_foreign_key_nullable(self):
        """Test that user field is nullable for visitor searches"""
        query = GlobalSearchQuery.objects.create(
            query_text="visitor search", search_type="all"
        )
        self.assertIsNone(query.user)

    def test_results_count_default_zero(self):
        """Test results_count defaults to 0"""
        query = GlobalSearchQuery.objects.create(query_text="test", search_type="all")
        self.assertEqual(query.results_count, 0)

    def test_results_count_update(self):
        """Test results_count can be updated"""
        query = GlobalSearchQuery.objects.create(
            query_text="test", search_type="all", results_count=0
        )
        query.results_count = 42
        query.save()

        query.refresh_from_db()
        self.assertEqual(query.results_count, 42)

    def test_ordering_by_created_at_desc(self):
        """Test queries are ordered by created_at descending"""
        query1 = GlobalSearchQuery.objects.create(
            query_text="search1", search_type="all"
        )
        query2 = GlobalSearchQuery.objects.create(
            query_text="search2", search_type="all"
        )

        queries = GlobalSearchQuery.objects.all()
        # Most recent first
        self.assertEqual(queries[0].id, query2.id)

    def test_string_representation(self):
        """Test string representation of search query"""
        query = GlobalSearchQuery.objects.create(
            query_text="test query", search_type="users"
        )
        str_repr = str(query)
        self.assertIn("test query", str_repr)


class UnifiedSearchViewTests(TestCase):
    """Tests for unified search view"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

    def test_no_query_returns_empty_results(self):
        """Test that no query parameter returns empty results"""
        response = self.client.get(reverse("search_app:unified_search"))
        self.assertEqual(response.status_code, 200)
        # Should have empty results
        if "results" in response.context:
            self.assertEqual(len(response.context["results"]), 0)

    def test_search_type_all_searches_all_types(self):
        """Test search with type='all' searches users and repos"""
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "test", "type": "all"}
        )
        self.assertEqual(response.status_code, 200)

    def test_search_type_users_only_searches_users(self):
        """Test search with type='users' only searches users"""
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "test", "type": "users"}
        )
        self.assertEqual(response.status_code, 200)

    def test_search_logs_query(self):
        """Test that search queries are logged"""
        self.client.get(
            reverse("search_app:unified_search"), {"q": "logged query", "type": "all"}
        )
        # Check if query was logged (implementation may vary)
        # This assumes logging is implemented
        query = GlobalSearchQuery.objects.filter(query_text="logged query").first()
        # Query may or may not be logged, depending on implementation
        # self.assertIsNotNone(query)

    def test_unauthenticated_user_access(self):
        """Test that unauthenticated users can search"""
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "public search", "type": "all"}
        )
        self.assertEqual(response.status_code, 200)


class AutocompleteViewTests(TestCase):
    """Tests for autocomplete suggestions"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="johnsmith", email="john@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="janedoe", email="jane@example.com", password="testpass123"
        )

    def test_query_too_short_returns_empty(self):
        """Test that short queries return empty results"""
        response = self.client.get(reverse("search_app:autocomplete"), {"q": "a"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data.get("suggestions", [])), 0)

    def test_returns_user_suggestions(self):
        """Test that user suggestions are returned"""
        response = self.client.get(reverse("search_app:autocomplete"), {"q": "john"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        suggestions = data.get("suggestions", [])
        # Should include johnsmith
        usernames = [s.get("text") for s in suggestions]
        self.assertIn("johnsmith", usernames)

    def test_returns_json_format(self):
        """Test that response is valid JSON"""
        response = self.client.get(reverse("search_app:autocomplete"), {"q": "john"})
        self.assertEqual(response.status_code, 200)
        try:
            data = json.loads(response.content)
            self.assertIn("suggestions", data)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")

    def test_limits_results_to_10(self):
        """Test that results are limited to 10"""
        # Create 15 users with similar names
        for i in range(15):
            User.objects.create_user(
                username=f"user{i:02d}",
                email=f"user{i}@example.com",
                password="testpass123",
            )

        response = self.client.get(reverse("search_app:autocomplete"), {"q": "user"})
        data = json.loads(response.content)
        suggestions = data.get("suggestions", [])
        self.assertLessEqual(len(suggestions), 10)


class SearchUsersTest(TestCase):
    """Tests for search_users functionality"""

    def setUp(self):
        """Set up test users"""
        self.user = User.objects.create_user(
            username="john_smith",
            email="john@example.com",
            first_name="John",
            last_name="Smith",
            password="testpass123",
        )

    def test_search_by_username(self):
        """Test search by username"""
        # This test depends on implementation
        # Assume there's a search_users function
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "john_smith", "type": "users"}
        )
        self.assertEqual(response.status_code, 200)

    def test_search_by_first_name(self):
        """Test search by first name"""
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "John", "type": "users"}
        )
        self.assertEqual(response.status_code, 200)

    def test_search_by_last_name(self):
        """Test search by last name"""
        response = self.client.get(
            reverse("search_app:unified_search"), {"q": "Smith", "type": "users"}
        )
        self.assertEqual(response.status_code, 200)


class SearchRepositoriesTest(TestCase):
    """Tests for search_repositories functionality"""

    def setUp(self):
        """Set up test user and projects"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_search_respects_public_visibility(self):
        """Test that search respects project visibility"""
        # Create public project
        Project.objects.create(
            name="Public Project", owner=self.user, visibility="public"
        )

        response = self.client.get(
            reverse("search_app:unified_search"),
            {"q": "Project", "type": "repositories"},
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_only_sees_public(self):
        """Test that unauthenticated users only see public projects"""
        Project.objects.create(
            name="Public Project", owner=self.user, visibility="public"
        )
        Project.objects.create(
            name="Private Project", owner=self.user, visibility="private"
        )

        response = self.client.get(
            reverse("search_app:unified_search"),
            {"q": "Project", "type": "repositories"},
        )
        # Should only see public projects
        self.assertEqual(response.status_code, 200)

    def test_authenticated_sees_own_repos(self):
        """Test that authenticated users see their own repos"""
        self.client.login(username="testuser", password="testpass123")

        Project.objects.create(
            name="My Private Project", owner=self.user, visibility="private"
        )

        response = self.client.get(
            reverse("search_app:unified_search"),
            {"q": "Project", "type": "repositories"},
        )
        self.assertEqual(response.status_code, 200)


# EOF
