#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth app views - modular structure.

This __init__.py re-exports all views to maintain backward compatibility
with existing code that imports from apps.auth_app.views.
"""
from __future__ import annotations

# Authentication views
from .authentication import (
    signup,
    login_view,
    logout_view,
)

# Password reset views
from .password_reset import (
    forgot_password,
    reset_password,
)

# Account management views
from .account import (
    verify_email,
    delete_account,
)

# Theme preference API views
from .theme import (
    api_save_theme_preference,
    api_get_theme_preference,
)

# Account switching views
from .account_switching import (
    get_or_create_device_id,
    add_authenticated_account,
    switch_account,
    get_authenticated_accounts,
)

__all__ = [
    # Authentication
    "signup",
    "login_view",
    "logout_view",
    # Password reset
    "forgot_password",
    "reset_password",
    # Account management
    "verify_email",
    "delete_account",
    # Theme preferences
    "api_save_theme_preference",
    "api_get_theme_preference",
    # Account switching
    "get_or_create_device_id",
    "add_authenticated_account",
    "switch_account",
    "get_authenticated_accounts",
]

# EOF
