#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/auth_app/views/authentication.py"""

import pytest

# from apps.infra.auth_app.views.authentication import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/auth_app/views/authentication.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """Authentication views: signup, login, logout."""
# from __future__ import annotations
# from django.shortcuts import render, redirect
# from django.contrib.auth import login, logout, authenticate
# from django.contrib import messages
# from django.contrib.auth.models import User
#
# from ..forms import SignupForm, LoginForm
# from ..models import UserProfile
#
#
# def signup(request):
#     """User signup view with email verification required."""
#     import logging
#     from apps.infra.project_app.services.email_service import EmailService
#
#     logger = logging.getLogger(__name__)
#
#     # Check visitor pool for unauthenticated users (browser requests only)
#     # Middleware should have auto-logged in visitor, if not authenticated then pool is likely exhausted
#     if not request.user.is_authenticated:
#         user_agent = request.META.get('HTTP_USER_AGENT', '')
#         is_browser = any(
#             browser in user_agent
#             for browser in ['Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge', 'Opera']
#         )
#         if is_browser:
#             logger.info("[Signup] Browser request not authenticated - redirecting to visitor-pool-full")
#             return redirect('public_app:visitor_pool_full')
#
#     if request.method == "POST":
#         form = SignupForm(request.POST)
#         if form.is_valid():
#             email = form.cleaned_data["email"]
#             username = form.cleaned_data["username"]
#             password = form.cleaned_data["password"]
#
#             # Check if email is already registered
#             if User.objects.filter(email=email).exists():
#                 messages.error(request, "An account with this email already exists.")
#                 return render(request, "auth_app/signup.html", {"form": form})
#
#             # Create inactive user (cannot log in until email verified)
#             user = User.objects.create_user(
#                 username=username,
#                 email=email,
#                 password=password,
#                 is_active=False,  # User inactive until email verified
#             )
#
#             # Create user profile (should be auto-created by signal, but ensure it exists)
#             UserProfile.objects.get_or_create(user=user)
#
#             # Create Gitea user account (sync with Gitea)
#             try:
#                 from apps.infra.gitea_app.services.gitea_sync_service import (
#                     sync_user_to_gitea,
#                 )
#
#                 sync_success = sync_user_to_gitea(user, password)
#                 if sync_success:
#                     logger.info(f"Gitea user created for {username}")
#                 else:
#                     logger.warning(f"Failed to create Gitea user for {username}")
#             except Exception as e:
#                 logger.warning(f"Gitea sync failed for {username}: {e}")
#                 # Don't fail signup if Gitea sync fails
#
#             # Migrate visitor session data if exists
#             if request.session.session_key:
#                 from apps.infra.project_app.services.anonymous_storage import (
#                     migrate_to_user_storage,
#                 )
#
#                 migrated = migrate_to_user_storage(request.session.session_key, user)
#                 if migrated:
#                     logger.info(
#                         f"Migrated visitor session data for new user {username}"
#                     )
#
#             # Claim visitor project if user was using visitor pool
#             # This transfers visitor-XXX's default-project to the new user's default-project
#             from apps.infra.project_app.services.visitor_pool import VisitorPool
#
#             claimed_project = VisitorPool.claim_project_on_signup(request.session, user)
#             if claimed_project:
#                 logger.info(
#                     f"Claimed visitor project for new user {username}: {claimed_project.id}"
#                 )
#             else:
#                 logger.info(f"No visitor project to claim for new user {username}")
#
#             # Create email verification record
#             from ..models import EmailVerification
#
#             verification = EmailVerification.objects.create(
#                 user=user,
#                 email=email,
#             )
#
#             # Send verification email
#             try:
#                 success, message = EmailService.send_otp_email(
#                     email=email, otp_code=verification.code, verification_type="signup"
#                 )
#
#                 if success:
#                     logger.info(f"Verification email sent to {email}")
#                     messages.success(
#                         request,
#                         f"Account created! Please check {email} for a verification code.",
#                     )
#                     # Redirect to email verification page
#                     from django.urls import reverse
#
#                     verify_url = reverse("auth_app:verify-email")
#                     return redirect(f"{verify_url}?email={email}")
#                 else:
#                     logger.error(
#                         f"Failed to send verification email to {email}: {message}"
#                     )
#                     # Don't delete user - let them retry verification
#                     messages.warning(
#                         request,
#                         f"Account created but verification email failed to send. "
#                         f"Please contact support or try logging in later.",
#                     )
#                     from django.urls import reverse
#
#                     verify_url = reverse("auth_app:verify-email")
#                     return redirect(f"{verify_url}?email={email}")
#             except Exception as e:
#                 logger.error(f"Error during signup for {email}: {str(e)}")
#                 # Don't delete user - keep the account
#                 messages.warning(
#                     request,
#                     f"Account created but there was an issue sending verification email. "
#                     f"Please contact support or try logging in later.",
#                 )
#                 from django.urls import reverse
#
#                 verify_url = reverse("auth_app:verify-email")
#                 return redirect(f"{verify_url}?email={email}")
#     else:
#         form = SignupForm()
#
#     context = {
#         "form": form,
#     }
#     return render(request, "auth_app/signup.html", context)
#
#
# def login_view(request):
#     """User login view with authentication."""
#     from .account_switching import add_authenticated_account
#
#     if request.method == "POST":
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             username = form.cleaned_data["username"]
#             password = form.cleaned_data["password"]
#
#             # Check if username is actually an email
#             if "@" in username:
#                 try:
#                     user_obj = User.objects.get(email=username)
#                     username = user_obj.username
#                 except User.DoesNotExist:
#                     pass
#
#             # Authenticate user
#             user = authenticate(request, username=username, password=password)
#
#             if user is not None:
#                 # Migrate visitor session data before login if exists
#                 if request.session.session_key:
#                     from apps.infra.project_app.services.anonymous_storage import (
#                         migrate_to_user_storage,
#                     )
#
#                     migrated = migrate_to_user_storage(
#                         request.session.session_key, user
#                     )
#                     if migrated:
#                         import logging
#
#                         logger = logging.getLogger(__name__)
#                         logger.info(
#                             f"Migrated visitor session data for user {user.username}"
#                         )
#                         messages.info(
#                             request,
#                             "Your previous session data has been saved to your account!",
#                         )
#
#                 login(request, user)
#
#                 # Handle remember me
#                 if not form.cleaned_data.get("remember_me"):
#                     request.session.set_expiry(0)
#
#                 # Redirect to next page or user's project page
#                 next_page = request.GET.get("next")
#                 if not next_page:
#                     # Default to user's project page (GitHub-style)
#                     from django.urls import reverse
#
#                     next_page = reverse(
#                         "project_app:user_profile", kwargs={"username": user.username}
#                     )
#
#                 messages.success(request, f"Welcome back, @{user.username}!")
#
#                 # Create response and register account for switching
#                 response = redirect(next_page)
#                 add_authenticated_account(request, response)
#                 return response
#             else:
#                 messages.error(request, "Invalid username or password.")
#     else:
#         form = LoginForm()
#
#     context = {
#         "form": form,
#     }
#     return render(request, "auth_app/signin.html", context)
#
#
# def logout_view(request):
#     """User logout view - clears all session data and redirects immediately."""
#     # Clear all session data before logout
#     request.session.flush()
#
#     # Logout user
#     logout(request)
#
#     # Redirect immediately without message (cleaner UX)
#     return redirect("/")
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/auth_app/views/authentication.py
# --------------------------------------------------------------------------------
