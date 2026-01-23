#!/usr/bin/env python3
"""
Test script for production login functionality.
Run this to verify ywata1989 login works in production.
"""

import os
import django
import sys

# Set up Django environment
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.contrib.auth.models import User
from apps.auth_app.models import UserProfile
from django.contrib.auth import authenticate

def test_production_login():
    print("🔍 Testing Production Login for ywata1989")
    print("=" * 50)
    
    # Check if user exists
    try:
        user = User.objects.get(username='ywata1989')
        print(f"✅ User found: {user.username} (ID: {user.id})")
        print(f"   Email: {user.email}")
        print(f"   Active: {user.is_active}")
        print(f"   Staff: {user.is_staff}")
    except User.DoesNotExist:
        print("❌ User ywata1989 not found in production database")
        return False
    
    # Check UserProfile
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"✅ UserProfile exists (ID: {profile.id})")
        print(f"   Academic verified: {profile.is_academic_verified}")
        print(f"   Profile completed: {profile.profile_completed}")
    except UserProfile.DoesNotExist:
        print("❌ UserProfile missing - this could cause login issues")
        return False
    
    # Test authentication
    auth_user = authenticate(username='ywata1989', password='ywata1989')
    if auth_user:
        print(f"✅ Authentication successful for {auth_user.username}")
    else:
        print("❌ Authentication failed - check password")
        return False
    
    # Check projects
    from apps.project_app.models import Project
    projects = Project.objects.filter(owner=user)
    print(f"📁 User has {projects.count()} projects")
    
    print("\n🎉 Production login should work!")
    print("Try logging in at: https://scitex.ai/login/")
    print("Username: ywata1989")
    print("Password: ywata1989")
    
    return True

if __name__ == "__main__":
    try:
        success = test_production_login()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
