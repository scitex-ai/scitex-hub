#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-22 06:53:31 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/tests/test_email.py
# ----------------------------------------
from __future__ import annotations
import os
__FILE__ = (
    "./tests/test_email.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
"""
Test email configuration and send test email.
"""

import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings


def test_email_config():
    """Test and display email configuration."""
    print("=" * 60)
    print("SciTeX Cloud Email Configuration Test")
    print("=" * 60)
    print()
    print(f"SCITEX_CLOUD_EMAIL_BACKEND: {settings.SCITEX_CLOUD_EMAIL_BACKEND}")
    print(f"SCITEX_CLOUD_EMAIL_HOST: {settings.SCITEX_CLOUD_EMAIL_HOST}")
    print(f"SCITEX_CLOUD_EMAIL_PORT: {settings.SCITEX_CLOUD_EMAIL_PORT}")
    print(f"SCITEX_CLOUD_EMAIL_USE_TLS: {getattr(settings, 'SCITEX_CLOUD_EMAIL_USE_TLS', False)}")
    print(f"SCITEX_CLOUD_EMAIL_USE_SSL: {getattr(settings, 'SCITEX_CLOUD_EMAIL_USE_SSL', False)}")
    print(f"SCITEX_CLOUD_EMAIL_HOST_USER: {settings.SCITEX_CLOUD_EMAIL_HOST_USER}")
    print(f"SCITEX_CLOUD_EMAIL_PASSWORD set: {bool(settings.SCITEX_CLOUD_EMAIL_HOST_PASSWORD)}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()


def send_test_email(recipient_email='ywata1989@gmail.com'):
    """Send a test email."""
    print("=" * 60)
    print(f"Sending test email to: {recipient_email}")
    print("=" * 60)
    print()

    try:
        # Get settings
        email_host = settings.SCITEX_CLOUD_EMAIL_HOST
        email_port = settings.SCITEX_CLOUD_EMAIL_PORT
        from_email = settings.DEFAULT_FROM_EMAIL
        use_tls = getattr(settings, 'SCITEX_CLOUD_EMAIL_USE_TLS', False)
        protocol = "TLS" if use_tls else "SSL"

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
    <link rel="shortcut icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
</head>
<body>
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #4a6baf;">SciTeX Cloud</h1>
        <h2>Test Email</h2>
    </div>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <p>This is a test email to verify SMTP configuration is working correctly.</p>
        <p>If you receive this email, password reset and other email features will work!</p>

        <div style="margin: 20px 0;">
            <h3 style="color: #4a6baf;">Configuration tested:</h3>
            <ul>
                <li>SMTP Server: {email_host}</li>
                <li>Port: {email_port} ({protocol})</li>
                <li>From: {from_email}</li>
            </ul>
        </div>
    </div>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
        <p>Best regards,<br>The SciTeX Team</p>
    </div>
</div>
</body>
</html>
"""


        plain_message = f'''
This is a test email to verify SMTP configuration is working correctly.

If you receive this email, password reset and other email features will work!

Configuration tested:
- SMTP Server: {email_host}
- Port: {email_port} ({protocol})
- From: {from_email}

Best regards,
The SciTeX Team
'''

        result = send_mail(
            subject='Test Email from SciTeX Cloud',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )

        print("✓ Email sent successfully!")
        print(f"  Result: {result} message(s) sent")
        return True

    except Exception as e:
        print(f"✗ Error sending email:")
        print(f"  {type(e).__name__}: {str(e)}")
        import traceback
        print()
        print("Full traceback:")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Test configuration
    test_email_config()

    # Send test email
    import sys
    recipient = sys.argv[1] if len(sys.argv) > 1 else 'ywata1989@gmail.com'
    send_test_email(recipient)

# EOF
