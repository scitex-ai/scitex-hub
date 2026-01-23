#!/usr/bin/env python3
"""
Test script for OTP email functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.workspace_app.services import EmailService
from apps.workspace_app.models import EmailVerification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_email_service():
    """Test the email service directly"""
    print("Testing OTP email service...")
    
    # Test with a dummy email
    test_email = "test@example.com"
    test_otp = "123456"
    
    try:
        success, message = EmailService.send_otp_email(
            email=test_email,
            otp_code=test_otp,
            verification_type='signup'
        )
        
        print(f"Email send result: Success={success}, Message={message}")
        return success
        
    except Exception as e:
        print(f"Error testing email service: {str(e)}")
        return False

def test_verification_creation():
    """Test OTP verification creation"""
    print("Testing OTP verification creation...")
    
    try:
        # Create a test verification
        verification = EmailVerification.create_verification(
            email="test@example.com",
            verification_type='signup',
            user=None
        )
        
        print(f"Verification created: OTP={verification.otp_code}, Expires={verification.expires_at}")
        return True
        
    except Exception as e:
        print(f"Error creating verification: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== SciTeX OTP Email Test ===")
    
    # Test verification creation
    verification_success = test_verification_creation()
    
    # Test email service
    email_success = test_email_service()
    
    print(f"\nResults:")
    print(f"- Verification creation: {'PASS' if verification_success else 'FAIL'}")
    print(f"- Email service: {'PASS' if email_success else 'FAIL'}")
    
    if verification_success and email_success:
        print("\n✅ OTP system is working correctly!")
    else:
