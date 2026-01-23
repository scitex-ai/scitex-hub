#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test forgot password functionality end-to-end.
"""

import argparse
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.test import Client
import json


def create_test_user():
    """Create a test user if it doesn't exist."""
    username = 'ywatanabe'
    email = 'ywata1989@gmail.com'

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': username}
    )

    if created:
        user.set_password('testpassword123')
        user.save()
        print(f"[+] Created test user: {username} ({email})")
    else:
        # Update username if needed
        if user.username != username:
            user.username = username
            user.save()
        print(f"[+] Test user already exists: {user.username} ({email})")

    return user


def test_forgot_password_api():
    """Test the forgot password API endpoint."""
    print("\n" + "=" * 60)
    print("Testing Forgot Password API")
    print("=" * 60)

    user = create_test_user()
    client = Client()

    # Test API endpoint
    print(f"\nSending password reset request for: {user.email}")

    response = client.post(
        '/api/v1/auth/forgot-password/',
        data=json.dumps({'email': user.email}),
        content_type='application/json'
    )

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.json()}")

    if response.status_code == 200:
        print("[PASS] Password reset request successful!")
        print("       Check your email for reset instructions")
        return True
    else:
        print("[FAIL] Password reset request failed!")
        return False


def test_password_reset_token():
    """Test password reset token generation and validation."""
    print("\n" + "=" * 60)
    print("Testing Password Reset Token Generation")
    print("=" * 60)

    user = create_test_user()

    # Generate token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    print(f"\nGenerated reset token for user: {user.username}")
    print(f"UID: {uid}")
    print(f"Token: {token}")

    # Create reset link
    reset_link = f"http://localhost:8000/reset-password/{uid}/{token}/"
    print(f"\nReset link: {reset_link}")

    # Validate token
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user_obj = User.objects.get(pk=user_id)
        is_valid = default_token_generator.check_token(user_obj, token)

        if is_valid:
            print("[PASS] Token is valid!")
            return True
        else:
            print("[FAIL] Token is invalid!")
            return False
    except Exception as e:
        print(f"[FAIL] Token validation error: {str(e)}")
        return False


def test_invalid_email():
    """Test forgot password with invalid email."""
    print("\n" + "=" * 60)
    print("Testing Invalid Email Handling")
    print("=" * 60)

    client = Client()

    # Test with non-existent email
    print("\nTesting with non-existent email: nonexistent@example.com")

    response = client.post(
        '/api/v1/auth/forgot-password/',
        data=json.dumps({'email': 'nonexistent@example.com'}),
        content_type='application/json'
    )

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.json()}")

    # Should still return success for security (don't reveal if email exists)
    if response.status_code == 200 and response.json().get('success'):
        print("[PASS] Correctly handles non-existent email (security best practice)")
        return True
    else:
        print("[FAIL] Invalid email handling failed")
        return False


def test_missing_email():
    """Test forgot password without email."""
    print("\n" + "=" * 60)
    print("Testing Missing Email Handling")
    print("=" * 60)

    client = Client()

    print("\nTesting without email parameter")

    response = client.post(
        '/api/v1/auth/forgot-password/',
        data=json.dumps({}),
        content_type='application/json'
    )

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.json()}")

    if response.status_code == 400:
        print("[PASS] Correctly rejects missing email")
        return True
    else:
        print("[FAIL] Should return 400 for missing email")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SciTeX Cloud - Forgot Password Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("API Endpoint", test_forgot_password_api()))
    results.append(("Token Generation", test_password_reset_token()))
    results.append(("Invalid Email", test_invalid_email()))
    results.append(("Missing Email", test_missing_email()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Test forgot password functionality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    # Run all tests
  %(prog)s --email test@example.com  # Test with specific email
  %(prog)s --api-only         # Test only API endpoint
  %(prog)s --token-only       # Test only token generation
        '''
    )

    parser.add_argument(
        '--email',
        type=str,
        help='Email address to use for testing (default: support@scitex.ai)'
    )

    parser.add_argument(
        '--api-only',
        action='store_true',
        help='Run only API endpoint test'
    )

    parser.add_argument(
        '--token-only',
        action='store_true',
        help='Run only token generation test'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Update test email if provided
    if args.email:
        # Update the email in create_test_user function
        global TEST_EMAIL
        TEST_EMAIL = args.email

    # Run specific tests if requested
    if args.api_only:
        print("\nRunning API endpoint test only...")
        result = test_forgot_password_api()
        sys.exit(0 if result else 1)
    elif args.token_only:
        print("\nRunning token generation test only...")
        result = test_password_reset_token()
        sys.exit(0 if result else 1)
    else:
        sys.exit(main())
