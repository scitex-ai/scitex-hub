#!/usr/bin/env python3
"""
Test web login functionality
"""
import os
import django
import sys

# Set up Django environment
sys.path.append('/home/ywatanabe/proj/SciTeX-Cloud')
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_web_login():
    """Test the web login functionality"""
    client = Client()
    
    # Test 1: GET login page
    print("Testing GET /login/...")
    response = client.get('/login/')
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Login page failed to load")
        print(f"Response content preview: {response.content[:500]}")
        return False
    
    print("✅ Login page loads successfully")
    
    # Test 2: POST login with valid credentials
    print("\nTesting POST /login/ with valid credentials...")
    response = client.post('/login/', {
        'username': 'ywata1989',
        'password': 'admin123'
    })
    
    print(f"Status: {response.status_code}")
    print(f"Redirect URL: {response.get('Location', 'No redirect')}")
    
    if response.status_code == 302:  # Redirect on successful login
        print("✅ Login successful - redirect detected")
        return True
    elif response.status_code == 200:
        # Check if there are error messages
        content = response.content.decode()
        if 'Invalid username or password' in content:
            print("❌ Login failed - invalid credentials error")
        else:
            print("❌ Login failed - form validation error")
        return False
    else:
        print(f"❌ Unexpected status code: {response.status_code}")
        return False

if __name__ == '__main__':
    print("Testing SciTeX Web Login...")
    print("=" * 40)
    
    # Check if user exists
    try:
        user = User.objects.get(username='ywata1989')
        print(f"User found: {user.username} ({user.email})")
        print(f"User active: {user.is_active}")
        print("=" * 40)
    except User.DoesNotExist:
        print("❌ User ywata1989 not found in database!")
        sys.exit(1)
    
    success = test_web_login()
    
    if success:
        print("\n🎉 Web login test PASSED!")
    else:
        print("\n💥 Web login test FAILED!")
