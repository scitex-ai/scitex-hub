#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account management views: email verification, account deletion."""
from __future__ import annotations
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def verify_email(request):
    """Email verification page for account signup."""
    return render(request, "auth_app/email_verification.html")


@login_required
def delete_account(request):
    """Delete user account with confirmation."""
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_text = request.POST.get("confirm_text", "")

        # Verify password
        user = authenticate(request, username=request.user.username, password=password)
        if user is None:
            messages.error(request, "Invalid password. Please try again.")
            return render(request, "auth_app/delete_account.html")

        # Verify confirmation text
        expected_text = f"delete {request.user.username}"
        if confirm_text.strip() != expected_text:
            messages.error(
                request, f"Please type exactly: delete {request.user.username}"
            )
            return render(request, "auth_app/delete_account.html")

        # Delete the account
        username = request.user.username
        request.user.delete()

        # Log out and show confirmation
        logout(request)
        messages.success(request, f"Account @{username} has been permanently deleted.")
        return redirect("public_app:index")

    return render(request, "auth_app/delete_account.html")


# EOF
