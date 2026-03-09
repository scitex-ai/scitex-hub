"""
Template tags for permission checking.
Clean syntax in templates.
"""

from django import template
from ..services import PermissionService

register = template.Library()


@register.filter
def can(user, permission_string):
    """
    Check if user has permission.

    Usage:
        {% if user|can:"write:writer:project" %}
            <button>Edit</button>
        {% endif %}

    Format: "action:module:project_obj"
    """
    try:
        parts = permission_string.split(":")
        action = parts[0]
        module = parts[1] if len(parts) > 1 else None
        project = parts[2] if len(parts) > 2 else None

        return PermissionService.check_permission(user, project, action, module)
    except (IndexError, AttributeError, ValueError):
        # Invalid permission string format or user is not authenticated
        return False


@register.simple_tag
def user_role(user, project):
    """
    Get user's role in project.

    Usage:
        {% user_role user project as role %}
        <span>You are: {{ role }}</span>
    """
    return PermissionService.get_user_role(user, project)


@register.filter
def can_edit_module(user, module_and_project):
    """
    Check if user can edit specific module.

    Usage:
        {% if user|can_edit_module:"writer,project_obj" %}
    """
    try:
        module, project = module_and_project.split(",")
        return PermissionService.can_write(user, project, module.strip())
    except (ValueError, AttributeError):
        # Invalid format (missing comma) or module/project is invalid
        return False
