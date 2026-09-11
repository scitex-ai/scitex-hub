#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Authentication views: signup, login, logout."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from ..forms import LoginForm, SignupForm
from ..models import UserProfile

#: THE ONE response for a signup attempt, used by EVERY outcome: a fresh
#: account, a resumed pending signup, a resend, an already-ACTIVE account and a
#: SPLIT collision. Deliberately conditional — "if that address can be used" —
#: because it has to be TRUE in all five cases, and because identical wording is
#: what stops the endpoint being an account-enumeration oracle. The actionable
#: routes (verify / sign in / reset) are offered to everyone, so offering them
#: signals nothing about whether this particular address exists.
_SIGNUP_RESPONSE_MESSAGE = (
    "If that address can be used for a SciTeX account, we've sent a "
    "verification code to it — check your inbox and spam folder. The code is "
    "valid for 60 minutes. If you already have an account, sign in instead, or "
    "reset your password if you've forgotten it."
)


def _send_pending_signup_code(request, user, email, logger) -> bool:
    """Issue a fresh verification code for a PENDING signup and mail it.

    Shared by the resume path so a resent code is created exactly the way the
    original one was — one code path, not two that can drift.
    """
    from apps.infra.project_app.services.email_service import EmailService

    from ..models import EmailVerification

    verification = EmailVerification.objects.create(user=user, email=email)
    try:
        success, message = EmailService.send_otp_email(
            email=email, otp_code=verification.code, verification_type="signup"
        )
    except Exception as exc:  # pragma: no cover - provider failures
        logger.error(f"Error re-sending verification for a pending signup: {exc}")
        return False
    if not success:
        logger.error(f"Failed to re-send verification email: {message}")
    return bool(success)


def signup(request):
    """User signup view with email verification required."""
    import logging

    from apps.infra.project_app.services.email_service import EmailService

    logger = logging.getLogger(__name__)

    # Signup page should always be accessible - no authentication required
    # Users come here specifically to create an account

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # LIFECYCLE DECISION (hub auth lifecycle P0). This block replaces a
            # dead end: the form used to reject any existing row before we got
            # here, so the inactive-account branch was unreachable and its
            # "wait 1 hour for the account to expire" advice pointed at an
            # expiry nothing ever performed.
            from ..models import EmailVerification
            from ..pending_signup import (
                SignupCollision,
                classify_pending_signup,
                record_resend,
                resend_allowed,
                resend_budget_message,
            )

            collision, existing_user = classify_pending_signup(email, username)

            if collision is SignupCollision.PENDING_EXPIRED and existing_user:
                # I3: an EXPIRED pending signup is RESUMABLE, and it is decided
                # HERE rather than by any sweep, so correctness does not depend
                # on the unscheduled cleanup command having run. The stale row
                # is inactive and never verified, so nothing of value is lost —
                # this is the deletion the original code intended but could
                # never reach. Falling through re-creates it with the values
                # just submitted, which also fixes the typo'd-password dead end.
                logger.info("Replacing expired pending signup")
                existing_user.delete()

            elif collision is SignupCollision.PENDING_LIVE:
                # I2/I5: inside the window the account stands; the only useful
                # action is another code, and that is rate limited per address.
                if not resend_allowed(email):
                    messages.warning(request, resend_budget_message())
                    return render(request, "auth_app/signup.html", {"form": form})
                record_resend(email)
                _send_pending_signup_code(request, existing_user, email, logger)
                messages.info(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            elif collision in (SignupCollision.ACTIVE, SignupCollision.SPLIT):
                # I1/I4: an ACTIVE account is never recreated and never deleted
                # here; SPLIT means two different accounts hold the submitted
                # email and username, so neither "create" nor "resume" is
                # correct and guessing would hijack a username or strand an
                # address. Both answer with the SAME message a real signup gets,
                # which is what stops the response being an enumeration oracle.
                logger.info("Signup attempt matched an existing account; generic reply")
                messages.info(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            # Create inactive user (cannot log in until email verified)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,  # User inactive until email verified
            )

            # Create user profile (should be auto-created by signal, but ensure it exists)
            UserProfile.objects.get_or_create(user=user)

            # Create Gitea user account (sync with Gitea)
            try:
                from apps.infra.gitea_app.services.gitea_sync_service import (
                    sync_user_to_gitea,
                )

                sync_success = sync_user_to_gitea(user, password)
                if sync_success:
                    logger.info(f"Gitea user created for {username}")
                else:
                    logger.warning(f"Failed to create Gitea user for {username}")
            except Exception as e:
                logger.warning(f"Gitea sync failed for {username}: {e}")
                # Don't fail signup if Gitea sync fails

            # Migrate visitor session data if exists
            if request.session.session_key:
                from apps.infra.project_app.services.anonymous_storage import (
                    migrate_to_user_storage,
                )

                migrated = migrate_to_user_storage(request.session.session_key, user)
                if migrated:
                    logger.info(
                        f"Migrated visitor session data for new user {username}"
                    )

            # Claim visitor project if user was using visitor pool
            # This transfers visitor-XXX's default-project to the new user's default-project
            from apps.infra.project_app.services.visitor_pool import VisitorPool

            claimed_project = VisitorPool.claim_project_on_signup(request.session, user)
            if claimed_project:
                logger.info(
                    f"Claimed visitor project for new user {username}: {claimed_project.id}"
                )
            else:
                logger.info(f"No visitor project to claim for new user {username}")

            # Create email verification record

            verification = EmailVerification.objects.create(
                user=user,
                email=email,
            )

            # Send verification email
            try:
                success, message = EmailService.send_otp_email(
                    email=email, otp_code=verification.code, verification_type="signup"
                )

                if success:
                    logger.info(f"Verification email sent to {email}")
                    # SAME message as every other outcome, deliberately — see
                    # _SIGNUP_RESPONSE_MESSAGE. A distinct "Account created!"
                    # here would be the enumeration oracle: identical wording
                    # for create/resend/resume/already-active is the point.
                    messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                    # Redirect to email verification page
                    from django.urls import reverse

                    verify_url = reverse("auth_app:verify_email")
                    return redirect(f"{verify_url}?email={email}")
                else:
                    logger.error(
                        f"Failed to send verification email to {email}: {message}"
                    )
                    # Don't delete user - let them retry verification
                    messages.warning(
                        request,
                        "Account created but verification email failed to send. "
                        "Please contact support or try logging in later.",
                    )
                    from django.urls import reverse

                    verify_url = reverse("auth_app:verify_email")
                    return redirect(f"{verify_url}?email={email}")
            except Exception as e:
                logger.error(f"Error during signup for {email}: {str(e)}")
                # Don't delete user - keep the account
                messages.warning(
                    request,
                    "Account created but there was an issue sending verification email. "
                    "Please contact support or try logging in later.",
                )
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")
    else:
        form = SignupForm()

    context = {
        "form": form,
    }
    return render(request, "auth_app/signup.html", context)


def login_view(request):
    """User login view with authentication."""
    from .account_switching import add_authenticated_account

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # Check if username is actually an email
            if "@" in username:
                try:
                    user_obj = User.objects.get(email=username)
                    username = user_obj.username
                except User.DoesNotExist:
                    pass

            # Authenticate user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Migrate visitor session data before login if exists
                if request.session.session_key:
                    from apps.infra.project_app.services.anonymous_storage import (
                        migrate_to_user_storage,
                    )

                    migrated = migrate_to_user_storage(
                        request.session.session_key, user
                    )
                    if migrated:
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.info(
                            f"Migrated visitor session data for user {user.username}"
                        )
                        messages.info(
                            request,
                            "Your previous session data has been saved to your account!",
                        )

                login(request, user)

                # Handle remember me
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)

                # Redirect to next page or user's project page
                next_page = request.GET.get("next")
                if not next_page:
                    # Default to hub root (Gitea-style project dashboard)
                    next_page = "/"

                messages.success(request, f"Welcome back, @{user.username}!")

                # Create response and register account for switching
                response = redirect(next_page)
                add_authenticated_account(request, response)
                return response
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    context = {
        "form": form,
    }
    return render(request, "auth_app/signin.html", context)


def logout_view(request):
    """User logout view - clears all session data and redirects immediately."""
    # Clear all session data before logout
    request.session.flush()

    # Logout user
    logout(request)

    # Redirect immediately without message (cleaner UX)
    return redirect("/")


# EOF
