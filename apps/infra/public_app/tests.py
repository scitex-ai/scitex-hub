from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import EmailVerification, SubscriptionPlan


class SubscriptionPlanTestCase(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Test Plan",
            plan_type="test",
            price_monthly=50,
            price_yearly=500,
            max_projects=10,
            storage_gb=100,
            cpu_cores=4,
            gpu_vram_gb=8,
        )

    def test_plan_creation(self):
        self.assertEqual(self.plan.name, "Test Plan")
        self.assertEqual(self.plan.price_monthly, 50)
        self.assertTrue(self.plan.is_active)

    def test_plan_string_representation(self):
        self.assertEqual(str(self.plan), "Test Plan - $50/month")


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_index_page(self):
        response = self.client.get(reverse("public_app:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SciTeX")

    def test_features_page(self):
        response = self.client.get(reverse("public_app:features"))
        self.assertEqual(response.status_code, 200)

    def test_pricing_page(self):
        # Create some test plans
        SubscriptionPlan.objects.create(
            name="Free", plan_type="free", price_monthly=0, max_projects=1, storage_gb=5
        )

        response = self.client.get(reverse("public_app:pricing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose Your SciTeX Plan")

    def test_api_docs_page(self):
        response = self.client.get(reverse("public_app:api_docs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Web API Documentation")

    def test_product_pages(self):
        product_urls = [
            "public_app:product-engine",
            "public_app:product-scholar",
            "public_app:product-code",
            "public_app:product-writer",
            "public_app:product-viz",
            "public_app:product-cloud",
        ]

        for url_name in product_urls:
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_legacy_product_redirects(self):
        """Test that legacy product URLs redirect correctly"""
        legacy_urls = [
            "public_app:product-search",
            "public_app:product-doc",
        ]

        for url_name in legacy_urls:
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 302)

    def test_login_page(self):
        response = self.client.get(reverse("public_app:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log In")

    def test_signup_page(self):
        response = self.client.get(reverse("public_app:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign Up")


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_login_with_username(self):
        response = self.client.post(
            reverse("public_app:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_login_with_email(self):
        response = self.client.post(
            reverse("public_app:login"),
            {"username": "test@example.com", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_invalid_login(self):
        response = self.client.post(
            reverse("public_app:login"),
            {"username": "wronguser", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)  # Stay on login page
        self.assertContains(response, "Invalid username or password")


class EmailVerificationTestCase(TestCase):
    def test_email_verification_creation(self):
        verification = EmailVerification.objects.create(email="test@example.com")
        self.assertIsNotNone(verification.code)
        self.assertEqual(len(verification.code), 6)
        self.assertFalse(verification.is_verified)
