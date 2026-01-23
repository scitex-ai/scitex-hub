"""
Database operations for WriterConsumer.
Uses Django 5.2 async ORM for optimal performance.
"""

from ..models import CollaborativeSession


class DatabaseMixin:
    """Mixin providing database operation methods for WriterConsumer."""

    async def check_access(self):
        """Check if user has access to manuscript."""
        if self.manuscript.owner_id == self.user.id:
            return True
        is_collaborator = await self.manuscript.collaborators.filter(
            id=self.user.id
        ).aexists()
        return is_collaborator

    async def create_session(self):
        """Create or update collaborative session."""
        session, created = await CollaborativeSession.objects.aupdate_or_create(
            manuscript=self.manuscript,
            user=self.user,
            session_id=self.channel_name,
            defaults={"is_active": True, "locked_sections": []},
        )
        return session

    async def end_session(self):
        """End collaborative session."""
        if hasattr(self, "session"):
            self.session.is_active = False
            await self.session.asave()

    async def get_active_collaborators(self):
        """Get list of currently active collaborators."""
        collaborators = []
        async for session in CollaborativeSession.objects.filter(
            manuscript=self.manuscript, is_active=True
        ).select_related("user"):
            if session.is_session_active():
                collaborators.append(
                    {
                        "user_id": session.user.id,
                        "username": session.user.username,
                        "locked_sections": session.locked_sections,
                    }
                )
        return collaborators

    async def log_change(self, section, operation):
        """Log document change to database."""
        from ..models import ManuscriptSection

        try:
            section_obj = await ManuscriptSection.objects.aget(
                manuscript=self.manuscript, section_type=section
            )
            # Note: DocumentChange model not found - placeholder for future implementation
            # await DocumentChange.objects.acreate(
            #     manuscript=self.manuscript,
            #     section=section_obj,
            #     user=self.user,
            #     session=self.session,
            #     change_type=operation.get("type", "insert"),
            #     operation_data=operation,
            # )
        except ManuscriptSection.DoesNotExist:
            pass

    async def update_cursor_position(self, section, position):
        """Update cursor position in session."""
        if hasattr(self, "session"):
            self.session.cursor_position = {"section": section, "position": position}
            await self.session.asave(update_fields=["cursor_position", "last_activity"])

    async def is_section_locked(self, section):
        """Check if section is locked by another user."""
        return (
            await CollaborativeSession.objects.filter(
                manuscript=self.manuscript,
                is_active=True,
                locked_sections__contains=[section],
            )
            .exclude(user=self.user)
            .aexists()
        )

    async def lock_section(self, section):
        """Lock a section for current user."""
        if hasattr(self, "session") and section not in self.session.locked_sections:
            self.session.locked_sections.append(section)
            await self.session.asave(update_fields=["locked_sections"])

    async def unlock_section(self, section):
        """Unlock a section for current user."""
        if hasattr(self, "session") and section in self.session.locked_sections:
            self.session.locked_sections.remove(section)
            await self.session.asave(update_fields=["locked_sections"])
