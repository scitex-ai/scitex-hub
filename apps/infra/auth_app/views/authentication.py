#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Authentication views: signup, login, logout."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from ..forms import LoginForm, SignupForm
from ..models import CODE_VALIDITY, PendingSignup, UserProfile

#: How long a code is valid, RENDERED FROM THE MODEL'S OWN CONSTANT rather than
#: retyped. The previous wording promised 60 minutes while the model enforced
#: 10 — a false claim in a message whose entire job is to be truthful about
#: what just happened. Deriving it means the two can never disagree again.
_CODE_VALIDITY_MINUTES = int(CODE_VALIDITY.total_seconds() // 60)

#: THE ONE response for a signup attempt, used by EVERY outcome: a fresh
#: account, a resumed pending signup, a resend, an already-ACTIVE account and
#: the collision cases. Deliberately conditional — "if that address can be
#: used" — because it has to be TRUE in all of them, and because identical
#: wording is what stops the endpoint being an account-enumeration oracle. The
#: actionable routes (verify / sign in / reset) are offered to everyone, so
#: offering them signals nothing about whether this address exists.
_SIGNUP_RESPONSE_MESSAGE = (
    "If that address can be used for a SciTeX account, we've sent a "
    "verification code to it — check your inbox and spam folder. The code is "
    f"valid for {_CODE_VALIDITY_MINUTES} minutes. If you already have an "
    "account, sign in instead, or reset your password if you've forgotten it."
)


def _send_pending_signup_code(request, user, email, logger) -> bool:
    """Issue a fresh verification code for a PENDING signup and mail it.

    Shared by the resume path so a resent code is created exactly the way the
    original one was — one code path, not two that can drift.
    """
    from apps.infra.project_app.services.email_service import EmailService

    from ..models import EmailVerification

    # DEFENCE IN DEPTH (PR #775 security hold). The classifier no longer hands
    # out a row the submitter has not proven, but the invariant belongs HERE as
    # well as there: a verification code is only ever minted for the identity
    # that will RECEIVE it. Binding user=<one row> with email=<someone else> IS
    # the takeover, so this refuses rather than trusting its caller — a future
    # call site must not be able to reintroduce the bug by accident.
    if (getattr(user, "email", "") or "").strip().lower() != (
        email or ""
    ).strip().lower():
        logger.error(
            "REFUSING to mint a verification code: the pending row's own email "
            "does not match the address the code would be sent to."
        )
        return False

    # DELIVERY-FIRST, ROLLBACK-SAFE (PR #775 sixth review, P0). The mint used to
    # be LEFT IN PLACE when the send failed or raised, and the verify endpoint
    # picks the NEWEST unverified row — so a failed resume stranded the previous
    # usable code behind a code nobody had received. The failure mode of the
    # recovery path was to destroy recovery. This is the same defect that was
    # fixed in resend_otp_api; this is its second call site, and the reason it
    # was worth fixing twice is that fixing one call site is not fixing a class.
    verification = EmailVerification.objects.create(user=user, email=email)
    try:
        success, message = EmailService.send_otp_email(
            email=email, otp_code=verification.code, verification_type="signup"
        )
    except Exception as exc:
        logger.error(f"Error re-sending verification for a pending signup: {exc}")
        verification.delete()
        return False
    if not success:
        logger.error(f"Failed to re-send verification email: {message}")
        verification.delete()
        return False
    return True


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
            from django.db import IntegrityError

            from ..models import EmailVerification
            from ..pending_signup import (
                SignupCollision,
                classify_and_reclaim,
                consume_resend_budget,
                resend_budget_message,
            )

            # ATOMIC, LOCKED, REVALIDATED (PR #775 third review). This used to
            # classify and then delete/re-create with NOTHING held in between, so
            # a concurrent verification could activate the row in that window and
            # the expired branch would delete a live account. classify_and_reclaim
            # re-reads the row under select_for_update and checks every
            # precondition again before it removes anything.
            collision, existing_user = classify_and_reclaim(email, username)

            if collision is SignupCollision.PENDING_EXPIRED and existing_user:
                # RE-ARM IN PLACE — NO DESTRUCTIVE REPLACEMENT (PR #775 fifth
                # review, P0). This branch deleted the stale row and let the flow
                # re-create it. The two halves were SEPARATE transactions: the
                # freed username was up for grabs by any concurrent request, and
                # a create/profile failure destroyed the old row — plus the Gitea
                # side effects already performed for it — with nothing to roll
                # back to.
                #
                # The request path now RE-ARMS the same row instead of replacing
                # it. Purging an abandoned address stays the cleanup command's
                # job, where it is deliberate and racing nothing.
                if not consume_resend_budget(email):
                    messages.warning(request, resend_budget_message())
                    return render(request, "auth_app/signup.html", {"form": form})
                _send_pending_signup_code(request, existing_user, email, logger)
                messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            elif collision is SignupCollision.PENDING_LIVE:
                # I2/I5: inside the window the account stands; the only useful
                # action is another code, and that is rate limited per address.
                # ATOMIC spend (PR #775 fourth review): check-then-record let
                # two parallel requests both pass the check and both send.
                if not consume_resend_budget(email):
                    messages.warning(request, resend_budget_message())
                    return render(request, "auth_app/signup.html", {"form": form})
                _send_pending_signup_code(request, existing_user, email, logger)
                messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            elif collision in (
                SignupCollision.ACTIVE,
                SignupCollision.SPLIT,
                SignupCollision.ONE_SIDED,
                SignupCollision.INACTIVE_NOT_PENDING,
            ):
                # I1/I4: an ACTIVE account is never recreated and never deleted
                # here; SPLIT means two different accounts hold the submitted
                # email and username; ONE_SIDED means only one of them matched
                # anything at all (PR #775 security hold — this used to be
                # treated as the matched row's own signup, which let a POST of
                # attacker_email + victim_username mint an OTP bound to the
                # victim and mail it to the attacker).
                #
                # All three answer with the SAME message a real signup gets and
                # touch NOTHING: no send, no delete, no password, no email
                # change, no login. That is what stops the response being an
                # enumeration oracle AND what stops it being a takeover.
                logger.info("Signup attempt matched an existing account; generic reply")
                messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            # Create inactive user (cannot log in until email verified)
            #
            # The insert can still LOSE A RACE (PR #775 third review): two
            # concurrent signups can both classify NONE and both reach here. The
            # database is the only arbiter that cannot race, so its verdict is
            # taken as a collision and answered with the SAME generic response
            # used everywhere else — never with a message that would confirm
            # which value was taken.
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=False,  # User inactive until email verified
                )
            except IntegrityError:
                logger.info("Signup insert lost a race; generic reply")
                messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                from django.urls import reverse

                verify_url = reverse("auth_app:verify_email")
                return redirect(f"{verify_url}?email={email}")

            # Create user profile (should be auto-created by signal, but ensure it exists)
            UserProfile.objects.get_or_create(user=user)

            # THE TYPED MARKER (PR #775 fifth review). This is the ONE place a
            # PendingSignup may be created, and it is what makes this account a
            # SIGNUP AWAITING VERIFICATION rather than merely an inactive row.
            # The verify, resend and cleanup paths all require it. Resend and
            # email-change deliberately never create one — that separation is
            # what stops a suspended account acquiring signup authority.
            PendingSignup.objects.create(user=user, email=email)

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
                    # GENERIC, like every other signup outcome (PR #775 review).
                    # A distinct "the email failed to send" told a caller that the
                    # account had JUST been created — i.e. that the address was
                    # NOT already registered. That is the same enumeration oracle
                    # the collision paths were unified to close.
                    messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
                    from django.urls import reverse

                    verify_url = reverse("auth_app:verify_email")
                    return redirect(f"{verify_url}?email={email}")
            except Exception as e:
                logger.error(f"Error during signup for {email}: {str(e)}")
                # Don't delete user - keep the account
                # GENERIC for the same reason as the branch above.
                messages.success(request, _SIGNUP_RESPONSE_MESSAGE)
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
