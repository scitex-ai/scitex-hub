#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API endpoints for email verification
"""

import json
import logging

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.email_service import EmailService

from .models import EmailVerification

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def verify_email_api(request):
    """API endpoint to verify email with OTP code"""
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        otp_code = data.get("otp_code", "").strip()

        if not email or not otp_code:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Email and verification code are required.",
                },
                status=400,
            )

        # Find the most recent verification for this email
        try:
            verification = (
                EmailVerification.objects.filter(email=email, is_verified=False)
                .order_by("-created_at")
                .first()
            )

            if not verification:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No pending verification found for this email.",
                    },
                    status=404,
                )

            # Check if verification has expired
            if verification.is_expired():
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Verification code has expired. Please request a new one.",
                    },
                    status=400,
                )

            # Verify the code
            #
            # Constant-time compare, and THROTTLED (PR #775 re-review). A
            # 6-digit code is only 10**6 possibilities: with no counter,
            # guessing was free and unlimited for the entire validity window,
            # which is what made the small keyspace matter. Five wrong guesses
            # burn the code; the owner then requests a fresh one, and that
            # request is itself rate limited.
            import secrets as _secrets

            if not _secrets.compare_digest(verification.code, otp_code):
                if verification.register_failed_attempt():
                    return JsonResponse(
                        {
                            "success": False,
                            "error": (
                                "Too many incorrect attempts. Please request a "
                                "new verification code."
                            ),
                        },
                        status=429,
                    )
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Invalid verification code. Please try again.",
                    },
                    status=400,
                )

            # DO NOT ACTIVATE BLINDLY (PR #775 fifth review, P0).
            #
            # verify() marked the row verified and the caller then set
            # is_active=True on whatever user the verification pointed at. That
            # made a code minted for an ADMIN-DISABLED account silently undo the
            # deactivation — a suspension bypass reachable with an email address.
            #
            # The gate has to run BEFORE verify(), because verify() itself
            # creates the verified row that has_pending_evidence() treats as a
            # disqualifying history. Email CHANGES are excluded: an active user
            # re-verifying a new address legitimately HAS that history.
            from apps.infra.auth_app.pending_signup import has_pending_evidence

            pending_change = request.session.get("pending_email_change")
            is_email_change = bool(
                pending_change and pending_change.get("new_email") == email
            )
            if not is_email_change and not has_pending_evidence(
                verification.user, verification.email
            ):
                logger.warning(
                    "Refusing to activate a row with no pending signup behind it"
                )
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "This account cannot be activated from here. "
                            "Please contact support."
                        ),
                    },
                    status=400,
                )

            # Mark verification as complete
            verification.verify()

            # LIFECYCLE: the signup is OVER the moment it is verified, so the
            # marker is DELETED here. It must not outlive the signup, or a later
            # administrator deactivation of this account would find a pending
            # marker and could be undone by the very path this fixes.
            # (For an email CHANGE there is no marker and this is a no-op.)
            from apps.infra.auth_app.models import PendingSignup

            PendingSignup.objects.filter(user=verification.user).delete()

            # Check if this is an email change verification
            pending_change = request.session.get("pending_email_change")
            if pending_change and pending_change.get("new_email") == email:
                # Update user's email
                user = User.objects.get(id=pending_change["user_id"])
                old_email = user.email
                user.email = email
                user.save()

                # Clear session
                del request.session["pending_email_change"]

                logger.info(
                    f"Email changed from {old_email} to {email} for user {user.username}"
                )
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Email updated successfully!",
                        "redirect_url": "/accounts/settings/account/",
                    }
                )

            # Regular signup verification
            # Activate the user
            user = verification.user
            user.is_active = True
            user.save()

            # Log the user in
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Send welcome email
            try:
                EmailService.send_welcome_email(user)
            except Exception as e:
                logger.warning(
                    f"Failed to send welcome email to {user.email}: {str(e)}"
                )

            logger.info(f"Email verified successfully for {email}")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Email verified successfully!",
                    "redirect_url": f"/{user.username}/",
                }
            )

        except EmailVerification.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Verification record not found."},
                status=404,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data."}, status=400
        )
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred during verification. Please try again.",
            },
            status=500,
        )


#: THE ONE resend response. Every non-malformed request gets this exact body
#: and status, whether or not an account exists, whether or not mail went out.
#: Different bodies for found/not-found made the endpoint an enumeration oracle
#: (PR #775 re-review).
_RESEND_RESPONSE = {
    "success": True,
    "message": (
        "If that address can be used for a SciTeX account, a new verification "
        "code has been sent. Check your inbox and spam folder."
    ),
}


@require_http_methods(["POST"])
def resend_otp_api(request):
    """API endpoint to resend OTP verification code.

    SECURITY (PR #775 re-review). Three removals of ways this endpoint was more
    useful to an attacker than to a user:

    1. CSRF PROTECTION RESTORED. It was ``@csrf_exempt`` — a state-changing
       POST (it mints a code and sends mail) that any third-party page could
       fire on a visitor's behalf.
    2. RATE LIMITED, and the budget is spent BEFORE the lookup, so a caller
       probing addresses that do not exist pays exactly what a caller mailing a
       real user pays. Previously unlimited: a mail-bomb at machine speed, and
       a way to invalidate a victim's outstanding code at will.
    3. ONE INDISTINGUISHABLE RESPONSE. "Account found" and "not found" used to
       return different bodies. Now every non-malformed request gets the same
       body and status. The 400 for a MISSING field is kept, because that is a
       fact about the REQUEST, not about any account.

    The code is bound to the ROW's own address (``user.email``), never to the
    submitted string, so this endpoint cannot be aimed at a third party either.
    """
    from django.db import transaction

    from apps.infra.auth_app.pending_signup import (
        consume_resend_budget,
        has_pending_evidence,
    )

    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()

        if not email:
            return JsonResponse(
                {"success": False, "error": "Email is required."}, status=400
            )

        # Spend the budget ATOMICALLY, before any lookup.
        if not consume_resend_budget(email):
            return JsonResponse(_RESEND_RESPONSE, status=200)

        user = User.objects.filter(email__iexact=email, is_active=False).first()
        # PENDING EVIDENCE REQUIRED (PR #775 fifth review, P0).
        #
        # Matching on is_active=False ALONE was a deactivation bypass: an
        # ADMIN-DISABLED account is inactive too, and this endpoint would mail it
        # a code that the verify endpoint then used to switch it back on. An
        # address was the only thing an attacker needed. No pending signup, no
        # code — and the response stays the single generic one either way.
        if user is None or not has_pending_evidence(user, email):
            return JsonResponse(_RESEND_RESPONSE, status=200)

        # DELIVERY FIRST, RETIRE SECOND (PR #775 fourth review). The old order
        # retired the outstanding code and THEN minted a replacement, so a send
        # failure left the user with NO working code: the failure mode of the
        # recovery path was to make recovery impossible. The previous code is
        # now retired only once the replacement has actually been delivered.
        with transaction.atomic():
            locked = User.objects.select_for_update().filter(pk=user.pk).first()
            if locked is None:
                return JsonResponse(_RESEND_RESPONSE, status=200)

            verification = EmailVerification.objects.create(
                user=locked,
                email=locked.email,
            )

            try:
                success, message = EmailService.send_otp_email(
                    email=locked.email,
                    otp_code=verification.code,
                    verification_type="signup",
                )
            except Exception as e:
                success, message = False, str(e)

            if not success:
                # Roll the mint back and KEEP the code that already worked.
                logger.error(f"Failed to resend verification email: {message}")
                verification.delete()
                return JsonResponse(_RESEND_RESPONSE, status=200)

            # Delivered: only now retire the codes it supersedes.
            EmailVerification.objects.filter(
                email__iexact=locked.email, is_verified=False
            ).exclude(pk=verification.pk).delete()

        return JsonResponse(_RESEND_RESPONSE, status=200)

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data."}, status=400
        )
    except Exception as e:
        logger.error(f"Error during OTP resend: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "An error occurred. Please try again."},
            status=500,
        )


@require_http_methods(["POST"])
def check_username_availability(request):
    """API endpoint to check if a username is available for registration"""
    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()

        if not username:
            return JsonResponse(
                {"available": False, "error": "Username is required."}, status=400
            )

        # Check if username is too short
        if len(username) < 1:
            return JsonResponse(
                {"available": False, "error": "Username must be at least 1 character."}
            )

        # Check if username is too long
        if len(username) > 39:
            return JsonResponse(
                {"available": False, "error": "Username cannot exceed 39 characters."}
            )

        # Reserved usernames (must match forms.py)
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
            return JsonResponse(
                {"available": False, "error": "This username is reserved."}
            )

        # Check if username already exists (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse(
                {"available": False, "error": "This username is already taken."}
            )

        # If we get here, username is available
        return JsonResponse({"available": True, "message": "Username is available!"})

    except json.JSONDecodeError:
        return JsonResponse(
            {"available": False, "error": "Invalid JSON data."}, status=400
        )
    except Exception as e:
        logger.error(f"Error checking username availability: {str(e)}")
        return JsonResponse(
            {"available": False, "error": "An error occurred. Please try again."},
            status=500,
        )


@csrf_exempt
@require_http_methods(["POST"])
def verify_credentials_api(request):
    """API endpoint for remote credential verification (orochi SSO fallback).

    Verifies username/password without creating a session.
    Returns user info on success for the remote app to create a local account.
    """
    from django.contrib.auth import authenticate as django_authenticate

    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return JsonResponse(
                {"success": False, "error": "Credentials required."}, status=400
            )

        # Allow login with email
        if "@" in username:
            try:
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Invalid credentials."}, status=401
                )

        user = django_authenticate(username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {"success": False, "error": "Invalid credentials."}, status=401
            )

        return JsonResponse(
            {
                "success": True,
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "name": user.get_full_name() or user.username,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)
