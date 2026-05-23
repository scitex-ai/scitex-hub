#!/usr/bin/env python3
"""
Comprehensive system validation for SciTeX Hub platform
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault(
    "SCITEX_CLOUD_DJANGO_SETTINGS_MODULE", "config.settings.development"
)
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.infra.workspace_app.models import UserProfile, EmailVerification
from apps.infra.workspace_app.services import EmailService
import json

User = get_user_model()


class SystemValidator:
    def __init__(self):
        self.client = Client()
        self.results = {"passed": 0, "failed": 0, "tests": []}

    def log_test(self, test_name, passed, message=""):
        status = "PASS" if passed else "FAIL"
        self.results["tests"].append(
            {"name": test_name, "status": status, "message": message}
        )
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        print(f"[{status}] {test_name}: {message}")

    def test_homepage(self):
        """Test homepage accessibility"""
        try:
            response = self.client.get("/")
            self.log_test(
                "Homepage Access",
                response.status_code == 200,
                f"Status: {response.status_code}",
            )
        except Exception as e:
            self.log_test("Homepage Access", False, str(e))

    def test_signup_page(self):
        """Test signup page accessibility"""
        try:
            response = self.client.get("/signup/")
            self.log_test(
                "Signup Page",
                response.status_code == 200,
                f"Status: {response.status_code}",
            )
        except Exception as e:
            self.log_test("Signup Page", False, str(e))

    def test_login_page(self):
        """Test login page accessibility"""
        try:
            response = self.client.get("/login/")
            self.log_test(
                "Login Page",
                response.status_code == 200,
                f"Status: {response.status_code}",
            )
        except Exception as e:
            self.log_test("Login Page", False, str(e))

    def test_email_verification_page(self):
        """Test email verification page"""
        try:
            response = self.client.get("/verify-email/")
            self.log_test(
                "Email Verification Page",
                response.status_code == 200,
                f"Status: {response.status_code}",
            )
        except Exception as e:
            self.log_test("Email Verification Page", False, str(e))

    def test_api_endpoints(self):
        """Test API endpoint accessibility"""
        endpoints = [
            "/api/v1/auth/register/",
            "/api/v1/auth/login/",
            "/api/v1/auth/verify-email/",
            "/api/v1/auth/resend-otp/",
        ]

        for endpoint in endpoints:
            try:
                response = self.client.get(endpoint)
                # API endpoints should return 405 (Method Not Allowed) for GET requests
                # This confirms they exist and are routing correctly
                expected_status = (
                    405 if "register" in endpoint or "verify" in endpoint else 200
                )
                passed = response.status_code in [
                    200,
                    405,
                    400,
                ]  # Any of these indicate endpoint exists
                self.log_test(
                    f"API Endpoint {endpoint}",
                    passed,
                    f"Status: {response.status_code}",
                )
            except Exception as e:
                self.log_test(f"API Endpoint {endpoint}", False, str(e))

    def test_module_interfaces(self):
        """Test SciTeX module interfaces"""
        modules = [
            ("/console/", "SciTeX Code"),
            ("/writer/", "SciTeX Writer"),
            ("/viz/", "SciTeX Viz"),
            ("/scholar/", "SciTeX Scholar"),
        ]

        for url, name in modules:
            try:
                response = self.client.get(url)
                # Modules might redirect to login or return 200
                passed = response.status_code in [200, 302]
                self.log_test(
                    f"{name} Interface", passed, f"Status: {response.status_code}"
                )
            except Exception as e:
                self.log_test(f"{name} Interface", False, str(e))

    def test_otp_system(self):
        """Test OTP verification system"""
        try:
            # Test OTP creation
            verification = EmailVerification.create_verification(
                email="test@example.com", verification_type="signup", user=None
            )
            self.log_test(
                "OTP Creation",
                bool(verification.otp_code),
                f"OTP: {verification.otp_code}",
            )

            # Test email service
            success, message = EmailService.send_otp_email(
                email="test@example.com",
                otp_code=verification.otp_code,
                verification_type="signup",
            )
            self.log_test("OTP Email Service", success, message)

            # Cleanup test verification
            verification.delete()

        except Exception as e:
            self.log_test("OTP System", False, str(e))

    def test_database_models(self):
        """Test database model operations"""
        try:
            # Test User model
            user_count = User.objects.count()
            self.log_test("User Model", True, f"User count: {user_count}")

            # Test UserProfile model
            profile_count = UserProfile.objects.count()
            self.log_test("UserProfile Model", True, f"Profile count: {profile_count}")

            # Test EmailVerification model
            verification_count = EmailVerification.objects.count()
            self.log_test(
                "EmailVerification Model",
                True,
                f"Verification count: {verification_count}",
            )

        except Exception as e:
            self.log_test("Database Models", False, str(e))

    def run_all_tests(self):
        """Run all validation tests"""
        print("🔄 Starting SciTeX Hub System Validation...")
        print("=" * 50)

        self.test_homepage()
        self.test_signup_page()
        self.test_login_page()
        self.test_email_verification_page()
        self.test_api_endpoints()
        self.test_module_interfaces()
        self.test_otp_system()
        self.test_database_models()

        print("=" * 50)
        print(
            f"✅ Validation Complete: {self.results['passed']} passed, {self.results['failed']} failed"
        )

        if self.results["failed"] == 0:
            print("🎉 All systems operational! SciTeX Hub is ready for use.")
        else:
            print("⚠️  Some issues found. Review failed tests above.")

        return self.results


if __name__ == "__main__":
    validator = SystemValidator()
