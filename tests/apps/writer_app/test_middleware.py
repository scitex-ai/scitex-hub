#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/writer_app/middleware.py"""

import pytest

# from apps.workspace.writer_app.middleware import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/writer_app/middleware.py
# --------------------------------------------------------------------------------
# """
# Custom middleware for WebSocket authentication.
# """
#
# from channels.db import database_sync_to_async
# from channels.middleware import BaseMiddleware
# from django.contrib.auth.models import VisitorUser
# from django.contrib.sessions.models import Session
# from django.contrib.auth import get_user_model
#
# User = get_user_model()
#
#
# class SessionAuthMiddleware(BaseMiddleware):
#     """
#     Custom middleware to authenticate WebSocket connections using session cookies.
#
#     Works with both regular users and visitor pool users.
#     """
#
#     async def __call__(self, scope, receive, send):
#         # Get session key from cookies
#         cookies = {}
#         for header_name, header_value in scope.get("headers", []):
#             if header_name == b"cookie":
#                 cookie_str = header_value.decode()
#                 for cookie in cookie_str.split(";"):
#                     if "=" in cookie:
#                         key, value = cookie.strip().split("=", 1)
#                         cookies[key] = value
#                 break
#
#         session_key = cookies.get("sessionid")
#
#         if session_key:
#             user = await self.get_user_from_session(session_key)
#             scope["user"] = user
#         else:
#             scope["user"] = VisitorUser()
#
#         return await super().__call__(scope, receive, send)
#
#     @database_sync_to_async
#     def get_user_from_session(self, session_key):
#         """Get user from session key."""
#         try:
#             session = Session.objects.get(session_key=session_key)
#             session_data = session.get_decoded()
#             user_id = session_data.get("_auth_user_id")
#
#             if user_id:
#                 return User.objects.get(pk=user_id)
#         except (Session.DoesNotExist, User.DoesNotExist):
#             pass
#
#         return VisitorUser()

# --------------------------------------------------------------------------------
# End of Source Code from: apps/writer_app/middleware.py
# --------------------------------------------------------------------------------
