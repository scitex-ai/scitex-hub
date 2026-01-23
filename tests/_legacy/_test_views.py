"""
SciTeX Web - View Tests
"""

from django.test import TestCase, Client
from django.urls import reverse


class IndexViewTests(TestCase):
    """Tests for the index view"""
    
    def setUp(self):
        self.client = Client()
    
    def test_index_view_returns_200(self):
        """Test that the index view returns a 200 OK response"""
        response = self.client.get(reverse('cloud_app:index'))
        self.assertEqual(response.status_code, 200)
    
    def test_index_view_uses_correct_template(self):
        """Test that the index view uses the correct template"""
        response = self.client.get(reverse('cloud_app:index'))
        self.assertTemplateUsed(response, 'cloud_app/landing.html')
    
    def test_index_view_contains_title(self):
        """Test that the index view contains the expected title"""
        response = self.client.get(reverse('cloud_app:index'))
        self.assertContains(response, 'SciTeX')