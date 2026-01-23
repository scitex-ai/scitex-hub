"""Account settings and integrations views."""
import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts_app.models import UserProfile

User = get_user_model()


def mask_token(token):
    """Mask authentication token for display."""
    if not token or len(token) < 8:
        return None
    return f"{token[:4]}...{token[-4:]}"


def handle_change_email(request):
    """Handle email change request."""
    new_email = request.POST.get("new_email", "").strip()
    if not new_email:
        messages.error(request, "Please enter a valid email address.")
        return False

    if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
        messages.error(request, "This email is already in use by another account.")
        return False

    # Send verification code to new email
    from apps.auth_app.models import EmailVerification
    from apps.project_app.services.email_service import EmailService

    # Store current email and pending new email in session
    request.session["pending_email_change"] = {
        "current_email": request.user.email,
        "new_email": new_email,
        "user_id": request.user.id,
    }

    # Generate and send OTP
    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    EmailVerification.objects.create(email=new_email, otp_code=otp_code)

    try:
        EmailService.send_verification_email(new_email, otp_code)
        messages.success(
            request,
            f"Verification code sent to {new_email}. Please check your inbox.",
        )
        # Redirect to email verification page
        request.session["email_change_redirect"] = True
        return True
    except Exception as e:
        messages.error(request, f"Failed to send verification email: {str(e)}")
        return False


def handle_change_password(request):
    """Handle password change request."""
    current_password = request.POST.get("current_password", "")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if not request.user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
        return False

    if new_password != confirm_password:
        messages.error(request, "New passwords do not match.")
        return False

    if len(new_password) < 8:
        messages.error(request, "Password must be at least 8 characters long.")
        return False

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)  # Keep user logged in
    messages.success(request, "Password updated successfully!")
    return True


@login_required
def account_settings(request):
    """Account settings page (email, password, delete account)."""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "change_email":
            if handle_change_email(request):
                return redirect(f"/auth/verify-email/?type=email_change")
        elif action == "change_password":
            handle_change_password(request)

        return redirect("accounts_app:account")

    context = {
        "user": request.user,
    }
    return render(request, "accounts_app/account_settings.html", context)


@login_required
def git_integrations(request):
    """Git Platform Integration settings page."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Update Git platform tokens
        github_token = request.POST.get("github_token", "").strip()
        gitlab_token = request.POST.get("gitlab_token", "").strip()
        bitbucket_token = request.POST.get("bitbucket_token", "").strip()

        if github_token:
            profile.github_token = github_token
        if gitlab_token:
            profile.gitlab_token = gitlab_token
        if bitbucket_token:
            profile.bitbucket_token = bitbucket_token

        # Update Git hosting profiles (public usernames)
        profile.github_profile = request.POST.get("github_profile", "").strip()
        profile.gitlab_profile = request.POST.get("gitlab_profile", "").strip()
        profile.bitbucket_profile = request.POST.get("bitbucket_profile", "").strip()

        profile.save()
        messages.success(request, "Git platform integrations updated successfully!")
        return redirect("accounts_app:git_integrations")

    context = {
        "profile": profile,
        "github_token_masked": mask_token(profile.github_token)
        if profile.github_token
        else None,
        "gitlab_token_masked": mask_token(profile.gitlab_token)
        if profile.gitlab_token
        else None,
        "bitbucket_token_masked": mask_token(profile.bitbucket_token)
        if profile.bitbucket_token
        else None,
    }
    return render(request, "accounts_app/git_integrations.html", context)
