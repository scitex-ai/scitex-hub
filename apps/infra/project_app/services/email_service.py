#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Email services for SciTeX Hub
# ----------------------------------------

import logging

from django.conf import settings
from django.core.mail import send_mail

from config import branding

logger = logging.getLogger(__name__)

# Get site URL from settings for generating absolute URLs
SITE_URL = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")

# Single source of truth: config/branding.py. Bound here the same way SITE_URL
# is, so the email bodies below can interpolate it like any other value.
CONTACT_EMAIL = branding.CONTACT_EMAIL


class EmailService:
    """Service for sending emails including OTP verification"""

    @staticmethod
    def send_otp_email(email, otp_code, verification_type="signup"):
        """Send OTP verification email"""
        try:
            # Determine email subject and context based on verification type
            if verification_type == "signup":
                subject = "SciTeX - Verify Your Email Address"
                template_name = "emails/signup_otp.html"
                context = {
                    "otp_code": otp_code,
                    "email": email,
                    "site_name": "SciTeX",
                    "expires_minutes": 10,
                    "verification_type": "account registration",
                }
            elif verification_type == "password_reset":
                subject = "SciTeX - Reset Your Password"
                template_name = "emails/password_reset_otp.html"
                context = {
                    "otp_code": otp_code,
                    "email": email,
                    "site_name": "SciTeX",
                    "expires_minutes": 10,
                    "verification_type": "password reset",
                }
            elif verification_type == "email_change":
                subject = "SciTeX - Verify Your New Email Address"
                template_name = "emails/email_change_otp.html"
                context = {
                    "otp_code": otp_code,
                    "email": email,
                    "site_name": "SciTeX",
                    "expires_minutes": 10,
                    "verification_type": "email address change",
                }
            else:
                raise ValueError(f"Unknown verification type: {verification_type}")

            # Create fallback plain text email if template doesn't exist
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
                <link rel="shortcut icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
            </head>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: left; margin-bottom: 30px;">
                    <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-logo-cropped.png" alt="SciTeX Logo" style="height: 60px; margin-bottom: 20px;">
                    <h2 style="margin-top: 20px;">Email Verification</h2>
                </div>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p>Hi there,</p>
                    <p>Use this verification code to complete your {context["verification_type"]}:</p>

                    <div style="text-align: center; margin: 30px 0;">
                        <div style="display: inline-block; background: #4a6baf; color: white; padding: 15px 30px; border-radius: 8px; font-size: 24px; font-weight: bold; letter-spacing: 3px;">
                            {otp_code}
                        </div>
                    </div>

                    <p><strong>Important:</strong></p>
                    <ul>
                        <li>This code expires in {context["expires_minutes"]} minutes</li>
                        <li>Your account must be verified within 1 hour or it will be deleted</li>
                        <li>Do not share this code with anyone</li>
                    </ul>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-icon/scitex-icon-navy-inverted-48x48.png" alt="SciTeX" style="height: 32px; opacity: 0.6;">
                    </div>
                    <p>If you didn't request this verification, please ignore this email.</p>
                    <p>This is an automated message from SciTeX Hub.</p>
                </div>
            </div>
            </body>
            </html>
            """

            plain_message = f"""
            SciTeX - Email Verification

            Hi there,

            Use this verification code to complete your {context["verification_type"]}:

            {otp_code}

            Important:
            - This code expires in {context["expires_minutes"]} minutes
            - Your account must be verified within 1 hour or it will be deleted
            - Do not share this code with anyone

            If you didn't request this verification, please ignore this email.

            This is an automated message from SciTeX Hub.
            """

            # Send email
            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )

            if result:
                logger.info(
                    f"OTP email sent successfully to {email} for {verification_type}"
                )
                return True, "Verification email sent successfully"
            else:
                logger.error(f"Failed to send OTP email to {email}")
                return False, "Failed to send verification email"

        except Exception as e:
            logger.error(f"Error sending OTP email to {email}: {str(e)}")
            return False, f"Error sending email: {str(e)}"

    @staticmethod
    def send_welcome_email(user):
        """Send welcome email after successful verification"""
        try:
            subject = "Welcome to SciTeX - Your Scientific Research Platform"

            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
                <link rel="shortcut icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
            </head>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: left; margin-bottom: 30px;">
                    <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-logo-cropped.png" alt="SciTeX Logo" style="height: 60px; margin-bottom: 20px;">
                    <h2 style="margin-top: 20px;">Welcome to Scientific Excellence!</h2>
                </div>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p>Hi {user.first_name or user.username},</p>
                    <p>Welcome to SciTeX! Your email has been verified and your account is now active.</p>

                    <div style="margin: 20px 0;">
                        <h3 style="color: #4a6baf;">What you can do now:</h3>
                        <ul>
                            <li><strong>SciTeX-Writer:</strong> Create and manage scientific documents</li>
                            <li><strong>SciTeX-Scholar:</strong> Search and explore scientific literature</li>
                            <li><strong>SciTeX-Code:</strong> Manage your research code and analysis</li>
                            <li><strong>SciTeX-Engine:</strong> AI-powered research assistance</li>
                            <li><strong>SciTeX-Viz:</strong> Create stunning scientific visualizations</li>
                        </ul>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{SITE_URL}/dashboard/" style="display: inline-block; background: #4a6baf; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                            Go to Dashboard
                        </a>
                    </div>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-icon/scitex-icon-navy-inverted-48x48.png" alt="SciTeX" style="height: 32px; opacity: 0.6;">
                    </div>
                    <p>Need help getting started? Check out our <a href="{SITE_URL}/docs/">documentation</a> or <a href="{SITE_URL}/contact/">contact support</a>.</p>
                    <p>Happy researching!</p>
                    <p>The SciTeX Team</p>
                </div>
            </div>
            </body>
            </html>
            """

            plain_message = f"""
            Welcome to SciTeX!

            Hi {user.first_name or user.username},

            Welcome to SciTeX! Your email has been verified and your account is now active.

            What you can do now:
            - SciTeX-Writer: Create and manage scientific documents
            - SciTeX-Scholar: Search and explore scientific literature
            - SciTeX-Code: Manage your research code and analysis
            - SciTeX-Engine: AI-powered research assistance
            - SciTeX-Viz: Create stunning scientific visualizations

            Visit your dashboard: {SITE_URL}/dashboard/

            Need help getting started? Check out our documentation at {SITE_URL}/docs/

            Happy researching!
            The SciTeX Team
            """

            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,  # Don't fail registration if welcome email fails
            )

            if result:
                logger.info(f"Welcome email sent to {user.email}")
            else:
                logger.warning(f"Failed to send welcome email to {user.email}")

            return result

        except Exception as e:
            logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
            return False

    @staticmethod
    def send_deletion_confirmation_email(user, deletion_date):
        """Send account deletion confirmation email"""
        try:
            subject = "SciTeX Account Deletion Scheduled"

            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
                <link rel="shortcut icon" type="image/png" href="https://scitex.ai/static/shared/images/favicon.png">
            </head>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: left; margin-bottom: 30px;">
                    <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-logo-cropped.png" alt="SciTeX Logo" style="height: 60px; margin-bottom: 20px;">
                    <h2 style="margin-top: 20px; color: #e74c3c;">Account Deletion Scheduled</h2>
                </div>

                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p><strong>Hi {user.first_name or user.username},</strong></p>
                    <p>Your SciTeX account has been scheduled for deletion.</p>

                    <div style="background: #ffffff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Deletion Details:</strong></p>
                        <ul>
                            <li><strong>Account:</strong> {user.email}</li>
                            <li><strong>Scheduled Date:</strong> {deletion_date.strftime("%B %d, %Y at %I:%M %p UTC")}</li>
                            <li><strong>Grace Period:</strong> 28 days</li>
                        </ul>
                    </div>

                    <p><strong>What happens next:</strong></p>
                    <ul>
                        <li>Your account will remain active for 28 days</li>
                        <li>You can cancel deletion anytime during this period</li>
                        <li>After 28 days, all your data will be permanently deleted</li>
                        <li>This includes: projects, documents, profile, and all associated data</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{SITE_URL}/dashboard/settings/" style="display: inline-block; background: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Cancel Deletion
                    </a>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    <div style="text-align: center; margin-bottom: 15px;">
                        <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-icon/scitex-icon-navy-inverted-48x48.png" alt="SciTeX" style="height: 32px; opacity: 0.6;">
                    </div>
                    <p>If you didn't request this deletion, please log in immediately and cancel it, then change your password.</p>
                    <p>Need help? Contact us at {CONTACT_EMAIL}</p>
                    <p>The SciTeX Team</p>
                </div>
            </div>
            </body>
            </html>
            """

            plain_message = f"""
            SciTeX Account Deletion Scheduled

            Hi {user.first_name or user.username},

            Your SciTeX account has been scheduled for deletion.

            Deletion Details:
            - Account: {user.email}
            - Scheduled Date: {deletion_date.strftime("%B %d, %Y at %I:%M %p UTC")}
            - Grace Period: 28 days

            What happens next:
            - Your account will remain active for 28 days
            - You can cancel deletion anytime during this period
            - After 28 days, all your data will be permanently deleted
            - This includes: projects, documents, profile, and all associated data

            To cancel deletion, visit: {SITE_URL}/dashboard/settings/

            If you didn't request this deletion, please log in immediately and cancel it, then change your password.

            Need help? Contact us at {CONTACT_EMAIL}

            The SciTeX Team
            """

            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            if result:
                logger.info(f"Account deletion confirmation email sent to {user.email}")
                return True, "Deletion confirmation email sent successfully"
            else:
                logger.error(
                    f"Failed to send deletion confirmation email to {user.email}"
                )
                return False, "Failed to send deletion confirmation email"

        except Exception as e:
            logger.error(
                f"Error sending deletion confirmation email to {user.email}: {str(e)}"
            )
            return False, f"Error sending email: {str(e)}"

    @staticmethod
    def send_app_submission_received(user, module_name):
        """Send confirmation email when an app is submitted for review."""
        try:
            subject = "SciTeX - App Submission Received"
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: left; margin-bottom: 30px;">
                    <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-logo-cropped.png" alt="SciTeX Logo" style="height: 60px; margin-bottom: 20px;">
                    <h2 style="margin-top: 20px;">App Submission Received</h2>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p>Hi {user.first_name or user.username},</p>
                    <p>Your app <strong>{module_name}</strong> has been submitted for review.</p>
                    <p>Our team will review your submission and you'll receive a notification once a decision is made. This usually takes 1-3 business days.</p>
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    <p>This is an automated message from SciTeX Hub.</p>
                </div>
            </div>
            </body>
            </html>
            """
            plain_message = f"""
            SciTeX - App Submission Received

            Hi {user.first_name or user.username},

            Your app {module_name} has been submitted for review.
            Our team will review your submission and you'll receive a notification
            once a decision is made. This usually takes 1-3 business days.

            This is an automated message from SciTeX Hub.
            """
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            logger.info(f"App submission email sent to {user.email} for {module_name}")
        except Exception as e:
            logger.error(f"Error sending submission email to {user.email}: {e}")

    @staticmethod
    def send_app_review_complete(user, module_name, status, note=""):
        """Send notification email when an app review decision is made."""
        try:
            status_labels = {
                "approved": (
                    "Approved",
                    "#28a745",
                    "Your app is now live in the marketplace!",
                ),
                "rejected": (
                    "Rejected",
                    "#dc3545",
                    "Unfortunately, your app did not pass review.",
                ),
                "changes_requested": (
                    "Changes Requested",
                    "#ffc107",
                    "Please address the reviewer's feedback and resubmit.",
                ),
            }
            label, color, description = status_labels.get(
                status, (status.title(), "#6c757d", "")
            )
            note_html = (
                f'<div style="background: #fff3cd; padding: 12px; border-radius: 4px; margin-top: 12px;"><strong>Reviewer note:</strong><br>{note}</div>'
                if note
                else ""
            )

            subject = f"SciTeX - App Review: {label}"
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: left; margin-bottom: 30px;">
                    <img src="{SITE_URL}/static/shared/images/scitex_logos/scitex-logo-cropped.png" alt="SciTeX Logo" style="height: 60px; margin-bottom: 20px;">
                    <h2 style="margin-top: 20px;">App Review Complete</h2>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p>Hi {user.first_name or user.username},</p>
                    <p>Your app <strong>{module_name}</strong> has been reviewed.</p>
                    <div style="display: inline-block; background: {color}; color: white; padding: 6px 16px; border-radius: 4px; font-weight: bold; margin: 8px 0;">
                        {label}
                    </div>
                    <p>{description}</p>
                    {note_html}
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    <p>This is an automated message from SciTeX Hub.</p>
                </div>
            </div>
            </body>
            </html>
            """
            note_plain = f"\nReviewer note: {note}" if note else ""
            plain_message = f"""
            SciTeX - App Review: {label}

            Hi {user.first_name or user.username},

            Your app {module_name} has been reviewed.
            Status: {label}
            {description}{note_plain}

            This is an automated message from SciTeX Hub.
            """
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            logger.info(f"App review email sent to {user.email}: {status}")
        except Exception as e:
            logger.error(f"Error sending review email to {user.email}: {e}")
