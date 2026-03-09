#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account switching functionality for multi-account support."""
from __future__ import annotations
from django.shortcuts import redirect
from django.contrib.auth import logout, login
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages


def get_or_create_device_id(request):
    """Get or create a unique device ID for this browser."""
    import uuid

    device_id = request.COOKIES.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    return device_id


def add_authenticated_account(request, response):
    """
    Register current user as authenticated on this device.
    Stores in database for persistence across sessions.
    """
    if not request.user.is_authenticated:
        return

    from ..models import AuthenticatedDevice, DeviceAccount

    # Get or create device ID
    device_id = get_or_create_device_id(request)

    # Set device ID cookie (if not already set)
    response.set_cookie(
        "device_id",
        device_id,
        max_age=365 * 24 * 60 * 60,  # 1 year
        httponly=True,
        samesite="Lax",
    )

    # Get or create device record
    device, _ = AuthenticatedDevice.objects.get_or_create(device_id=device_id)

    # Add user to this device (if not already added)
    DeviceAccount.objects.get_or_create(device=device, user=request.user)


def switch_account(request, user_id):
    """
    Switch to another account that user has previously authenticated to.
    Only allows switching between accounts authenticated on THIS device.
    """
    from ..models import AuthenticatedDevice, DeviceAccount

    # Get device ID
    device_id = request.COOKIES.get("device_id")
    if not device_id:
        messages.error(request, "No device ID found")
        return redirect("/")

    try:
        device = AuthenticatedDevice.objects.get(device_id=device_id)
    except AuthenticatedDevice.DoesNotExist:
        messages.error(request, "Device not found")
        return redirect("/")

    # Check if target user is authenticated on this device
    try:
        device_account = DeviceAccount.objects.get(device=device, user_id=user_id)
    except DeviceAccount.DoesNotExist:
        messages.error(
            request,
            "You can only switch to accounts you've previously logged into on this device",
        )
        return redirect("/")

    # Store the return URL
    return_url = request.GET.get("next", request.META.get("HTTP_REFERER", "/"))

    # Logout current user
    logout(request)

    # Login as target user
    target_user = device_account.user
    login(request, target_user, backend="django.contrib.auth.backends.ModelBackend")

    # Update last_used timestamp
    device_account.save()  # Triggers auto_now on last_used

    messages.success(request, f"Switched to: {target_user.username}")

    return HttpResponseRedirect(return_url)


def get_authenticated_accounts(request):
    """
    API endpoint to get list of accounts authenticated on this device.
    Returns accounts from database based on device ID.
    """
    from ..models import AuthenticatedDevice, DeviceAccount

    if not request.user.is_authenticated:
        return JsonResponse({"accounts": []})

    # Get device ID
    device_id = request.COOKIES.get("device_id")
    if not device_id:
        return JsonResponse({"accounts": [], "current_user_id": request.user.id})

    try:
        device = AuthenticatedDevice.objects.get(device_id=device_id)
        device_accounts = DeviceAccount.objects.filter(device=device).select_related(
            "user"
        )

        accounts = [
            {
                "user_id": da.user.id,
                "username": da.user.username,
                "full_name": da.user.get_full_name() or da.user.username,
            }
            for da in device_accounts
        ]

        return JsonResponse({"accounts": accounts, "current_user_id": request.user.id})

    except AuthenticatedDevice.DoesNotExist:
        return JsonResponse({"accounts": [], "current_user_id": request.user.id})


# EOF
