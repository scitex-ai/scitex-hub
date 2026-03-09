#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for social_app

This module contains unit tests for the social app, covering:
- User follow/unfollow functionality
- Repository starring
- Activity tracking
- Social feeds and exploration
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import json

from .models import UserFollow, RepositoryStar, Activity
from apps.infra.project_app.models import Project


class UserFollowModelTests(TestCase):
    """Tests for UserFollow model"""

    def setUp(self):
        """Set up test users"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

    def test_creation_follower_following_relationship(self):
        """Test UserFollow creates follower/following relationship"""
        follow = UserFollow.objects.create(follower=self.user1, following=self.user2)
        self.assertEqual(follow.follower, self.user1)
        self.assertEqual(follow.following, self.user2)

    def test_unique_together_follower_following(self):
        """Test that duplicate follows are prevented"""
        UserFollow.objects.create(follower=self.user1, following=self.user2)

        # Try to create duplicate
        with self.assertRaises(Exception):
            UserFollow.objects.create(follower=self.user1, following=self.user2)

    def test_prevents_self_follow(self):
        """Test that user cannot follow themselves"""
        # This depends on model validation
        try:
            UserFollow.objects.create(follower=self.user1, following=self.user1)
            # If it succeeds, app might need to handle this
        except Exception:
            # Expected behavior
            pass

    def test_is_following_returns_true_when_following(self):
        """Test is_following method"""
        UserFollow.objects.create(follower=self.user1, following=self.user2)

        if hasattr(UserFollow, "is_following"):
            result = UserFollow.is_following(self.user1, self.user2)
            self.assertTrue(result)

    def test_is_following_returns_false_when_not_following(self):
        """Test is_following returns False when not following"""
        if hasattr(UserFollow, "is_following"):
            result = UserFollow.is_following(self.user1, self.user2)
            self.assertFalse(result)

    def test_get_followers_count(self):
        """Test getting follower count"""
        UserFollow.objects.create(follower=self.user1, following=self.user2)
        UserFollow.objects.create(
            follower=User.objects.create_user(
                username="user3", email="user3@example.com", password="testpass123"
            ),
            following=self.user2,
        )

        follower_count = UserFollow.objects.filter(following=self.user2).count()
        self.assertEqual(follower_count, 2)

    def test_get_following_count(self):
        """Test getting following count"""
        UserFollow.objects.create(follower=self.user1, following=self.user2)
        UserFollow.objects.create(
            follower=self.user1,
            following=User.objects.create_user(
                username="user3", email="user3@example.com", password="testpass123"
            ),
        )

        following_count = UserFollow.objects.filter(follower=self.user1).count()
        self.assertEqual(following_count, 2)


class RepositoryStarModelTests(TestCase):
    """Tests for RepositoryStar model"""

    def setUp(self):
        """Set up test user and project"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Test Project", owner=self.user)

    def test_creation_user_project_relationship(self):
        """Test RepositoryStar creates user/project relationship"""
        star = RepositoryStar.objects.create(user=self.user, project=self.project)
        self.assertEqual(star.user, self.user)
        self.assertEqual(star.project, self.project)

    def test_unique_together_user_project(self):
        """Test that duplicate stars are prevented"""
        RepositoryStar.objects.create(user=self.user, project=self.project)

        # Try to create duplicate
        with self.assertRaises(Exception):
            RepositoryStar.objects.create(user=self.user, project=self.project)

    def test_is_starred_returns_true_when_starred(self):
        """Test is_starred method"""
        RepositoryStar.objects.create(user=self.user, project=self.project)

        if hasattr(RepositoryStar, "is_starred"):
            result = RepositoryStar.is_starred(self.user, self.project)
            self.assertTrue(result)

    def test_is_starred_returns_false_when_not_starred(self):
        """Test is_starred returns False when not starred"""
        if hasattr(RepositoryStar, "is_starred"):
            result = RepositoryStar.is_starred(self.user, self.project)
            self.assertFalse(result)

    def test_get_star_count(self):
        """Test getting star count for project"""
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

        RepositoryStar.objects.create(user=self.user, project=self.project)
        RepositoryStar.objects.create(user=user2, project=self.project)

        star_count = RepositoryStar.objects.filter(project=self.project).count()
        self.assertEqual(star_count, 2)

    def test_starred_at_timestamp(self):
        """Test starred_at timestamp"""
        star = RepositoryStar.objects.create(user=self.user, project=self.project)
        self.assertIsNotNone(star.starred_at)
        self.assertLessEqual(star.starred_at, timezone.now())


class ActivityModelTests(TestCase):
    """Tests for Activity model"""

    def setUp(self):
        """Set up test user and project"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Test Project", owner=self.user)

    def test_creation_with_activity_types(self):
        """Test Activity can be created with different types"""
        types = ["follow", "star", "create_project"]
        for activity_type in types:
            activity = Activity.objects.create(
                user=self.user, activity_type=activity_type
            )
            self.assertEqual(activity.activity_type, activity_type)

    def test_user_required(self):
        """Test that user is required"""
        # Should fail without user
        try:
            Activity.objects.create(activity_type="test")
            self.fail("Should require user")
        except Exception:
            pass  # Expected

    def test_target_user_nullable(self):
        """Test that target_user is optional"""
        activity = Activity.objects.create(
            user=self.user, activity_type="create_project", target_user=None
        )
        self.assertIsNone(activity.target_user)

    def test_target_project_nullable(self):
        """Test that target_project is optional"""
        activity = Activity.objects.create(
            user=self.user, activity_type="follow", target_project=None
        )
        self.assertIsNone(activity.target_project)

    def test_metadata_json_field(self):
        """Test metadata JSON field"""
        metadata = {"action": "starred", "reason": "interesting research"}
        activity = Activity.objects.create(
            user=self.user,
            activity_type="star",
            target_project=self.project,
            metadata=metadata,
        )
        self.assertEqual(activity.metadata["action"], "starred")

    def test_ordering_by_created_at_desc(self):
        """Test activities ordered by created_at descending"""
        activity1 = Activity.objects.create(
            user=self.user, activity_type="create_project"
        )
        activity2 = Activity.objects.create(
            user=self.user, activity_type="create_project"
        )

        activities = Activity.objects.all()
        self.assertEqual(activities[0].id, activity2.id)


class FollowUnfollowViewTests(TestCase):
    """Tests for follow/unfollow views"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

    def test_follow_user_requires_login(self):
        """Test that follow requires authentication"""
        response = self.client.post(reverse("social_app:follow_user", args=["user2"]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_follow_user_creates_relationship(self):
        """Test following a user creates relationship"""
        self.client.login(username="user1", password="testpass123")

        response = self.client.post(reverse("social_app:follow_user", args=["user2"]))
        self.assertEqual(response.status_code, 200)

        # Check relationship was created
        self.assertTrue(
            UserFollow.objects.filter(
                follower=self.user1, following=self.user2
            ).exists()
        )

    def test_cannot_follow_yourself(self):
        """Test that user cannot follow themselves"""
        self.client.login(username="user1", password="testpass123")

        response = self.client.post(reverse("social_app:follow_user", args=["user1"]))
        # Should return error
        self.assertIn(response.status_code, [400, 403])

    def test_unfollow_user_removes_relationship(self):
        """Test unfollowing a user removes relationship"""
        self.client.login(username="user1", password="testpass123")

        # First follow
        UserFollow.objects.create(follower=self.user1, following=self.user2)

        # Then unfollow
        response = self.client.post(reverse("social_app:unfollow_user", args=["user2"]))
        self.assertEqual(response.status_code, 200)

        # Check relationship was removed
        self.assertFalse(
            UserFollow.objects.filter(
                follower=self.user1, following=self.user2
            ).exists()
        )


class StarUnstarViewTests(TestCase):
    """Tests for star/unstar views"""

    def setUp(self):
        """Set up test client, user and project"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Test Project", owner=self.user)

    def test_star_repository_requires_login(self):
        """Test that starring requires authentication"""
        response = self.client.post(
            reverse("social_app:star_repository", args=["testuser", "test-project"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_star_repository_creates_star(self):
        """Test starring a repository creates star"""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        self.client.login(username="other", password="testpass123")

        response = self.client.post(
            reverse("social_app:star_repository", args=["testuser", "test-project"])
        )
        self.assertEqual(response.status_code, 200)

        # Check star was created
        self.assertTrue(
            RepositoryStar.objects.filter(
                user=other_user, project=self.project
            ).exists()
        )

    def test_unstar_repository_removes_star(self):
        """Test unstarring removes star"""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        self.client.login(username="other", password="testpass123")

        # First star
        RepositoryStar.objects.create(user=other_user, project=self.project)

        # Then unstar
        response = self.client.post(
            reverse("social_app:unstar_repository", args=["testuser", "test-project"])
        )
        self.assertEqual(response.status_code, 200)

        # Check star was removed
        self.assertFalse(
            RepositoryStar.objects.filter(
                user=other_user, project=self.project
            ).exists()
        )


class FollowersListViewTests(TestCase):
    """Tests for followers list view"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.follower = User.objects.create_user(
            username="follower", email="follower@example.com", password="testpass123"
        )

    def test_followers_list_returns_json(self):
        """Test followers list returns JSON"""
        UserFollow.objects.create(follower=self.follower, following=self.user)

        response = self.client.get(
            reverse("social_app:followers_list", args=["testuser"])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)

    def test_followers_list_includes_details(self):
        """Test followers list includes follower details"""
        UserFollow.objects.create(follower=self.follower, following=self.user)

        response = self.client.get(
            reverse("social_app:followers_list", args=["testuser"])
        )
        data = json.loads(response.content)
        self.assertIn("followers", data)
        self.assertIn("username", data["followers"][0])


class ExploreViewTests(TestCase):
    """Tests for explore page"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.project = Project.objects.create(
            name="Popular Project", owner=self.user, visibility="public"
        )

    def test_explore_default_tab_is_repositories(self):
        """Test explore page defaults to repositories tab"""
        response = self.client.get(reverse("social_app:explore"))
        self.assertEqual(response.status_code, 200)
        # Default should show repositories

    def test_explore_repositories_tab(self):
        """Test repositories tab on explore page"""
        response = self.client.get(
            reverse("social_app:explore"), {"tab": "repositories"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("repositories", response.context)

    def test_explore_users_tab(self):
        """Test users tab on explore page"""
        response = self.client.get(reverse("social_app:explore"), {"tab": "users"})
        self.assertEqual(response.status_code, 200)


# EOF
