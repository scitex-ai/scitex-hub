"""
Permission service - centralized permission logic.
Single source of truth for all authorization decisions.
"""

from typing import Optional
from .models import Role, ProjectMember


class PermissionService:
    """Centralized permission checking."""

    # Role hierarchy (higher number = more permissions)
    ROLE_HIERARCHY = {
        Role.GUEST: 0,
        Role.REPORTER: 1,
        Role.DEVELOPER: 2,
        Role.MAINTAINER: 3,
        Role.OWNER: 4,
    }

    @classmethod
    def get_user_role(cls, user, project) -> Optional[str]:
        """Get user's role in project."""
        # Owner always has owner role
        if project.owner == user:
            return Role.OWNER

        # Check ProjectMember
        try:
            member = ProjectMember.objects.get(
                project=project, user=user, is_active=True
            )
            return member.role
        except ProjectMember.DoesNotExist:
            return None

    @classmethod
    def can_read(cls, user, project) -> bool:
        """Can user read project content?"""
        role = cls.get_user_role(user, project)
        return role is not None  # All roles can read

    @classmethod
    def can_write(cls, user, project, module: Optional[str] = None) -> bool:
        """Can user write/edit content?"""
        role = cls.get_user_role(user, project)
        if not role:
            return False

        # Guest and Reporter cannot write
        if role in [Role.GUEST, Role.REPORTER]:
            return False

        # Check module-specific permission if provided
        if module:
            try:
                member = ProjectMember.objects.get(project=project, user=user)
                module_perm = getattr(member, f"can_edit_{module}", None)
                if module_perm is not None:
                    return module_perm  # Explicit override
            except ProjectMember.DoesNotExist:
                pass

        # Developer, Maintainer, Owner can write
        return cls.ROLE_HIERARCHY[role] >= cls.ROLE_HIERARCHY[Role.DEVELOPER]

    @classmethod
    def can_delete(cls, user, project) -> bool:
        """Can user delete resources?"""
        role = cls.get_user_role(user, project)
        return role in [Role.MAINTAINER, Role.OWNER]

    @classmethod
    def can_manage(cls, user, project) -> bool:
        """Can user manage settings/collaborators?"""
        role = cls.get_user_role(user, project)
        return role in [Role.MAINTAINER, Role.OWNER]

    @classmethod
    def can_admin(cls, user, project) -> bool:
        """Can user perform admin actions (delete project, transfer ownership)?"""
        return project.owner == user

    @classmethod
    def can_invite(cls, user, project) -> bool:
        """Can user invite collaborators?"""
        role = cls.get_user_role(user, project)
        return role in [Role.MAINTAINER, Role.OWNER]

    @classmethod
    def can_compile(cls, user, project) -> bool:
        """Can user compile/run analyses?"""
        role = cls.get_user_role(user, project)
        return cls.ROLE_HIERARCHY.get(role, 0) >= cls.ROLE_HIERARCHY[Role.REPORTER]

    @classmethod
    def check_permission(
        cls, user, project, action: str, module: Optional[str] = None
    ) -> bool:
        """
        Universal permission check.

        Args:
            user: User to check
            project: Project context
            action: 'read', 'write', 'delete', 'manage', 'admin', 'invite', 'compile'
            module: Optional module name for module-specific checks

        Returns:
            True if user has permission
        """
        if action == "read":
            return cls.can_read(user, project)
        elif action == "write":
            return cls.can_write(user, project, module)
        elif action == "delete":
            return cls.can_delete(user, project)
        elif action == "manage":
            return cls.can_manage(user, project)
        elif action == "admin":
            return cls.can_admin(user, project)
        elif action == "invite":
            return cls.can_invite(user, project)
        elif action == "compile":
            return cls.can_compile(user, project)
        else:
            return False
