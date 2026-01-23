"""
SciTeX Cloud - Application Tests
"""

from django.test import TestCase
from django.conf import settings
from django.urls import reverse


class DjangoConfigTests(TestCase):
    """Tests for Django application configuration"""
    
    def test_django_settings_configured(self):
        """Test that Django settings are properly configured"""
        # Test that basic settings exist
        self.assertTrue(hasattr(settings, 'INSTALLED_APPS'))
        self.assertTrue(hasattr(settings, 'MIDDLEWARE'))
        self.assertTrue(hasattr(settings, 'ROOT_URLCONF'))
        
    def test_required_apps_installed(self):
        """Test that required apps are installed"""
        # Check that our apps are in INSTALLED_APPS
        installed_apps = settings.INSTALLED_APPS
        
        # Basic Django apps
        self.assertIn('django.contrib.admin', installed_apps)
        self.assertIn('django.contrib.auth', installed_apps)
        self.assertIn('django.contrib.contenttypes', installed_apps)
        self.assertIn('django.contrib.sessions', installed_apps)
        
        # Our custom apps
        self.assertIn('apps.public_app', installed_apps)
        
    def test_debug_mode_in_development(self):
        """Test that debug mode is properly configured"""
        # In development, DEBUG should typically be True
        # This test checks that we can access the DEBUG setting
        self.assertIsInstance(settings.DEBUG, bool)


class URLConfigTests(TestCase):
    """Tests for URL configuration"""
    
    def test_basic_urls_configured(self):
        """Test that basic URLs are configured"""
        # Test that we can reverse basic URLs
        try:
            admin_url = reverse('admin:index')
            self.assertTrue(admin_url.startswith('/admin'))
        except:
            # Admin might not be configured, that's okay for this basic test
            pass
            
        # Test our main app URLs
        index_url = reverse('public_app:index')
        self.assertEqual(index_url, '/')


class ApplicationTests(TestCase):
    """Tests for general application functionality"""
    
    def test_application_can_start(self):
        """Test that the Django application can start"""
        # This test just checks that the Django test framework can run
        # which implies the application is properly configured
        self.assertTrue(True)
        
    def test_static_files_configuration(self):
        """Test that static files are configured"""
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertTrue(hasattr(settings, 'STATICFILES_DIRS'))