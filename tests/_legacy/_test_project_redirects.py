#!/usr/bin/env python3
"""
Test project redirect functionality
"""
import os
import django
import sys

# Set up Django environment
sys.path.append('/home/ywatanabe/proj/SciTeX-Cloud')
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_project_redirects():
    """Test the project redirect functionality"""
    client = Client()
    
    print("Testing Project Redirect Functionality")
    print("=" * 50)
    
    # Test 1: Visitor user accessing /projects/
    print("1. Testing visitor user access to /projects/...")
    response = client.get('/projects/', follow=True)
    print(f"   Status: {response.status_code}")
    print(f"   Final URL: {response.request['PATH_INFO']}")
    if 'login' in response.request['PATH_INFO']:
        print("   ✅ Correctly redirected to login page")
    else:
        print("   ❌ Not redirected to login page")
    
    # Test 2: Create a test user and login
    print("\n2. Testing logged-in user access to /projects/...")
    
    # Create or get test user
    try:
        user = User.objects.get(username='ywata1989')
        print(f"   Using existing user: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
        print(f"   Created test user: {user.username}")
    
    # Login the user
    login_success = client.login(username=user.username, password='admin123' if user.username == 'ywata1989' else 'testpass')
    print(f"   Login successful: {login_success}")
    
    if login_success:
        # Test logged-in user redirect
        response = client.get('/projects/', follow=True)
        print(f"   Status: {response.status_code}")
        print(f"   Final URL: {response.request['PATH_INFO']}")
        expected_url = f"/{user.username}/"
        if response.request['PATH_INFO'] == expected_url:
            print(f"   ✅ Correctly redirected to {expected_url}")
        else:
            print(f"   ❌ Expected redirect to {expected_url}")
    
    # Test 3: Direct access to username URL
    print(f"\n3. Testing direct access to /{user.username}/...")
    response = client.get(f'/{user.username}/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ User profile page loads successfully")
    else:
        print("   ❌ User profile page failed to load")

if __name__ == '__main__':
    test_project_redirects()
