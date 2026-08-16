#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-26 19:41:52 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/auth_app/urls.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/auth_app/urls.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

from django.urls import path

from . import api_views, views
from .account_linking import views as account_linking_views

app_name = "auth_app"

urlpatterns = [
    # Identity surface for the cards board — "who is this session?".
    path(
        "api/whoami/",
        account_linking_views.whoami,
        name="api_whoami",
    ),
    path("signup/", views.signup, name="signup"),
    path("signin/", views.login_view, name="signin"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signout/", views.logout_view, name="signout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path(
        "reset-password/<str:uidb64>/<str:token>/",
        views.reset_password,
        name="reset_password",
    ),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("delete-account/", views.delete_account, name="delete_account"),
    # API endpoints for email verification
    path(
        "api/verify-email/",
        api_views.verify_email_api,
        name="api_verify_email",
    ),
    path("api/resend-otp/", api_views.resend_otp_api, name="api_resend_otp"),
    # API endpoints for signup validation
    path(
        "api/check-username/",
        api_views.check_username_availability,
        name="api_check_username",
    ),
    # API endpoint for remote credential verification (orochi)
    path(
        "api/login/",
        api_views.verify_credentials_api,
        name="api_verify_credentials",
    ),
    # API endpoints for theme preferences
    path(
        "api/save-theme/",
        views.api_save_theme_preference,
        name="api_save_theme",
    ),
    path("api/get-theme/", views.api_get_theme_preference, name="api_get_theme"),
    # Account switcher (multi-account support)
    path("switch/<int:user_id>/", views.switch_account, name="switch_account"),
    path(
        "api/authenticated-accounts/",
        views.get_authenticated_accounts,
        name="api_authenticated_accounts",
    ),
]

# EOF
