"""
SciTeX Cloud - API Tests
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json


class AuthAPITests(TestCase):
    """Tests for the Authentication API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # API endpoints  
        self.register_url = reverse('api:api-register')
        self.login_url = reverse('api:api-login')
    
    def test_register_new_user(self):
        """Test registering a new user"""
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(user_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Parse response
        data = json.loads(response.content)
        
        # Check response structure for email verification flow
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        self.assertIn('email', data)
        self.assertIn('verification_required', data)
        self.assertEqual(data['email'], 'newuser@example.com')
        self.assertTrue(data['verification_required'])
    
    def test_login_with_valid_credentials(self):
        """Test login with valid credentials"""
        # Create test user
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        login_data = {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Parse response
        data = json.loads(response.content)
        
        # Check response structure
        self.assertTrue(data['success'])
        self.assertIn('tokens', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        
        # Parse response
        data = json.loads(response.content)
        
        # Check response structure
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class BasicAPITests(TestCase):
    """Tests for basic API functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
    
    def test_api_endpoints_exist(self):
        """Test that basic API endpoints exist"""
        # Test registration endpoint exists
        response = self.client.get(reverse('api:api-register'))
        self.assertNotEqual(response.status_code, 404)
        
        # Test login endpoint exists  
        response = self.client.get(reverse('api:api-login'))
        self.assertNotEqual(response.status_code, 404)