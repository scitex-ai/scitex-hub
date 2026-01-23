"""
SciTeX Cloud - Django Model Tests
"""

from django.test import TestCase
from django.contrib.auth.models import User


class UserModelTests(TestCase):
    """Tests for Django User model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_create_user(self):
        """Test creating a new user"""
        user = User.objects.create_user(**self.user_data)
        
        # Check user properties
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpassword123'))
    
    def test_user_str_representation(self):
        """Test string representation of User model"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser')
    
    def test_user_is_active_by_default(self):
        """Test that users are active by default"""
        user = User.objects.create_user(**self.user_data)
        self.assertTrue(user.is_active)


class BasicModelTests(TestCase):
    """Tests for basic model functionality"""
    
    def test_django_models_importable(self):
        """Test that Django models can be imported"""
        from django.contrib.auth.models import User
        from django.contrib.auth.models import Group
        
        # Test that we can create basic Django objects
        self.assertTrue(hasattr(User, 'objects'))
        self.assertTrue(hasattr(Group, 'objects'))