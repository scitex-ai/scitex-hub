"""
Organization settings views.

GitHub-style org settings: General, Members, Repositories, Security, Danger Zone.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Organization, OrganizationMembership

logger = logging.getLogger(__name__)


def _get_org_and_check_admin(request, username):
    """Get org by slug (from URL username param) and verify admin. Raises Http404 if not."""
    org = get_object_or_404(Organization, slug=username)
    if not org.can_edit(request.user):
        raise Http404("You do not have permission to manage this organization.")
    return org


@login_required
def org_settings(request, username):
    """GET /<org-slug>/settings/ — Org settings page (General tab)."""
    org = _get_org_and_check_admin(request, username)
    return render(
        request,
        "organizations_app/settings/settings_page.html",
        {"organization": org, "active_section": "general"},
    )


@login_required
def org_settings_section(request, username, section):
    """GET /<org-slug>/settings/<section>/ — Render a settings section partial."""
    org = _get_org_and_check_admin(request, username)
    valid_sections = ["general", "members", "repositories", "security", "danger"]
    if section not in valid_sections:
        raise Http404(f"Unknown settings section: {section}")

    template = f"organizations_app/settings/{section}_section.html"
    context = {"organization": org, "active_section": section}

    # Add extra context for members section
    if section == "members":
        context["memberships"] = OrganizationMembership.objects.filter(
            organization=org
        ).select_related("user")

    # Add extra context for repositories section
    if section == "repositories":
        from apps.infra.project_app.models import Project

        context["repositories"] = Project.objects.filter(org_owner=org).order_by(
            "-updated_at"
        )

    # Return just the section partial for AJAX requests
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, template, context)

    # Full page render for direct navigation
    context["section_template"] = template
    return render(
        request,
        "organizations_app/settings/settings_page.html",
        context,
    )


# ----- API endpoints (AJAX) -----


@login_required
@require_POST
def api_update_general(request, username):
    """POST /<org-slug>/settings/api/general/ — Update org profile."""
    org = _get_org_and_check_admin(request, username)

    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    website = request.POST.get("website", "").strip()

    if name:
        org.name = name
    org.description = description
    org.website = website

    if "avatar" in request.FILES:
        org.avatar = request.FILES["avatar"]

    org.save()
    return JsonResponse({"success": True})


@login_required
@require_POST
def api_add_member(request, username):
    """POST /<org-slug>/settings/api/members/add/ — Invite a member."""
    org = _get_org_and_check_admin(request, username)

    member_username = request.POST.get("username", "").strip()
    role = request.POST.get("role", "member")

    if role not in ["admin", "member", "viewer"]:
        return JsonResponse({"success": False, "error": "Invalid role"}, status=400)

    try:
        user = User.objects.get(username=member_username)
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": f"User '{member_username}' not found"},
            status=404,
        )

    _, created = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=org,
        defaults={"role": role},
    )
    if not created:
        return JsonResponse(
            {"success": False, "error": f"'{member_username}' is already a member"},
            status=409,
        )

    return JsonResponse({"success": True, "username": member_username, "role": role})


@login_required
@require_POST
def api_update_member_role(request, username):
    """POST /<org-slug>/settings/api/members/role/ — Change member role."""
    org = _get_org_and_check_admin(request, username)

    member_username = request.POST.get("username", "").strip()
    role = request.POST.get("role", "").strip()

    if role not in ["admin", "member", "viewer"]:
        return JsonResponse({"success": False, "error": "Invalid role"}, status=400)

    membership = OrganizationMembership.objects.filter(
        organization=org, user__username=member_username
    ).first()
    if not membership:
        return JsonResponse({"success": False, "error": "Member not found"}, status=404)

    membership.role = role
    membership.save(update_fields=["role"])
    return JsonResponse({"success": True})


@login_required
@require_POST
def api_remove_member(request, username):
    """POST /<org-slug>/settings/api/members/remove/ — Remove a member."""
    org = _get_org_and_check_admin(request, username)

    member_username = request.POST.get("username", "").strip()

    # Prevent removing yourself if you're the last admin
    admin_count = OrganizationMembership.objects.filter(
        organization=org, role="admin"
    ).count()
    if member_username == request.user.username and admin_count <= 1:
        return JsonResponse(
            {"success": False, "error": "Cannot remove the last admin"},
            status=400,
        )

    deleted, _ = OrganizationMembership.objects.filter(
        organization=org, user__username=member_username
    ).delete()
    if not deleted:
        return JsonResponse({"success": False, "error": "Member not found"}, status=404)
    return JsonResponse({"success": True})


@login_required
@require_POST
def api_delete_org(request, username):
    """POST /<org-slug>/settings/api/delete/ — Delete organization."""
    org = _get_org_and_check_admin(request, username)

    confirm_name = request.POST.get("confirm_name", "").strip()
    if confirm_name != org.name:
        return JsonResponse(
            {
                "success": False,
                "error": "Organization name does not match. Deletion cancelled.",
            },
            status=400,
        )

    org.delete()
    return JsonResponse({"success": True, "redirect": "/"})


# EOF
