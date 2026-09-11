#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from django import forms


class SignupForm(forms.Form):
    """Form for user registration."""

    username = forms.CharField(
        max_length=39,  # GitHub's maximum username length
        min_length=1,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Choose a username (e.g., john-doe-42)",
            }
        ),
        help_text="Username may only contain alphanumeric characters, hyphens, and underscores. Cannot begin or end with a hyphen.",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "your.email@example.com"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Create a strong password"}
        )
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm your password"}
        ),
        label="Confirm Password",
    )
    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="I agree to the Terms of Service and Privacy Policy",
    )

    def clean_username(self):
        """Validate username follows GitHub-style rules and is unique."""
        username = self.cleaned_data["username"]

        # GitHub-style validation rules
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-_]*[a-zA-Z0-9])?$", username):
            raise forms.ValidationError(
                "Username may only contain alphanumeric characters, hyphens, and underscores. "
                "Username cannot begin or end with a hyphen or underscore, and cannot contain consecutive hyphens."
            )

        # Check for consecutive hyphens (GitHub doesn't allow this)
        if "--" in username:
            raise forms.ValidationError("Username cannot contain consecutive hyphens.")

        # Reserved usernames (like GitHub)
        reserved_usernames = [
            "admin",
            "administrator",
            "api",
            "auth",
            "billing",
            "blog",
            "cloud",
            "code",
            "core",
            "dashboard",
            "dev",
            "docs",
            "help",
            "login",
            "logout",
            "project",
            "projects",
            "scholar",
            "signup",
            "static",
            "support",
            "terms",
            "privacy",
            "about",
            "contact",
            "settings",
            "user",
            "users",
            "viz",
            "writer",
            "root",
            "system",
            "scitex",
        ]
        if username.lower() in reserved_usernames:
            raise forms.ValidationError("This username is reserved.")

        # NO UNIQUENESS CHECK HERE, deliberately (hub auth lifecycle P0).
        #
        # This validator used to raise "This username is already taken." for any
        # existing row, which made signup()'s inactive-account resume/expiry
        # branch UNREACHABLE: form.is_valid() was already False, so a pending
        # signup could never be resumed and its owner was told to "wait 1 hour
        # for the account to expire" — advice that led nowhere, because the
        # expiry branch it referred to could not run either.
        #
        # Existence is a LIFECYCLE question with four answers (create / resend /
        # resume / refuse) and a field validator can only say "no". It is
        # decided in the view via auth_app.pending_signup.classify_pending_signup,
        # so the response can be both actionable and non-enumerating.
        return username

    def clean_email(self):
        """Normalise the address. Existence is NOT decided here.

        Same reason as ``clean_username``: a uniqueness error here would mask
        the pending/resume path. See auth_app.pending_signup for the lifecycle
        and for why the answer must not reveal whether an address is known.
        """
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        """Validate passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class LoginForm(forms.Form):
    """Form for user login."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Username or Email"}
        ),
        label="Username or Email",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        )
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Remember me",
    )


# EOF
