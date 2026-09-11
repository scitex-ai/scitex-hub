#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth app views - modular structure.

This __init__.py re-exports all views to maintain backward compatibility
with existing code that imports from apps.infra.auth_app.views.
"""

from __future__ import annotations

# Account management views
from .account import (
    delete_account,
    verify_email,
)

# Account switching views
from .account_switching import (
    add_authenticated_account,
    get_authenticated_accounts,
    get_or_create_device_id,
    switch_account,
)

# Authentication views
from .authentication import (
    login_view,
    logout_view,
    signup,
)

# Password reset views
from .password_reset import (
    forgot_password,
    reset_password,
)

# Theme preference API views
from .theme import (
    api_get_theme_preference,
    api_save_theme_preference,
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
