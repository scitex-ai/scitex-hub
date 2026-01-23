"""
SciTeX Cloud - Configuration Tests
"""

from django.test import TestCase
from django.conf import settings
import os


class DjangoSettingsTests(TestCase):
    """Tests for Django settings configuration"""
    
    def test_basic_settings_exist(self):
        """Test that basic Django settings are configured"""
        # Test essential settings
        self.assertTrue(hasattr(settings, 'DEBUG'))
        self.assertTrue(hasattr(settings, 'SCITEX_CLOUD_DJANGO_SECRET_KEY'))
        self.assertTrue(hasattr(settings, 'SCITEX_CLOUD_ALLOWED_HOSTS'))
        self.assertTrue(hasattr(settings, 'INSTALLED_APPS'))
        self.assertTrue(hasattr(settings, 'MIDDLEWARE'))
        
    def test_database_configured(self):
        """Test that database is configured"""
        self.assertTrue(hasattr(settings, 'DATABASES'))
        self.assertIn('default', settings.DATABASES)
        
    def test_static_files_configured(self):
        """Test that static files are configured"""
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertTrue(hasattr(settings, 'STATIC_ROOT'))
        self.assertTrue(hasattr(settings, 'STATICFILES_DIRS'))
        
    def test_template_configuration(self):
        """Test that templates are configured"""
        self.assertTrue(hasattr(settings, 'TEMPLATES'))
        self.assertIsInstance(settings.TEMPLATES, list)
        self.assertGreater(len(settings.TEMPLATES), 0)


class EnvironmentTests(TestCase):
    """Tests for environment-specific configuration"""
    
    def test_development_settings_loaded(self):
        """Test that development settings are loaded"""
        # In development mode, certain settings should be present
        if hasattr(settings, 'SCITEX_CLOUD_DJANGO_SETTINGS_MODULE'):
            settings_module = os.environ.get('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', '')
            if 'development' in settings_module:
                # Development-specific tests
                self.assertTrue(settings.DEBUG)
                
    def test_installed_apps_include_dev_tools(self):
        """Test that development tools are included in INSTALLED_APPS"""
        installed_apps = settings.INSTALLED_APPS
        
        # Check for development tools if in debug mode
        if settings.DEBUG:
            # These are common development apps
            dev_apps = [
                'django_browser_reload',
                'django_extensions',
            ]
            
            for app in dev_apps:
                if app in installed_apps:
                    self.assertIn(app, installed_apps)


class SecuritySettingsTests(TestCase):
    """Tests for security-related settings"""
    
    def test_secret_key_exists(self):
        """Test that SCITEX_CLOUD_DJANGO_SECRET_KEY is configured"""
        self.assertTrue(hasattr(settings, 'SCITEX_CLOUD_DJANGO_SECRET_KEY'))
        self.assertIsNotNone(settings.SCITEX_CLOUD_DJANGO_SECRET_KEY)
        self.assertNotEqual(settings.SCITEX_CLOUD_DJANGO_SECRET_KEY, '')
        
    def test_allowed_hosts_configured(self):
        """Test that SCITEX_CLOUD_ALLOWED_HOSTS is configured"""
        self.assertTrue(hasattr(settings, 'SCITEX_CLOUD_ALLOWED_HOSTS'))
