#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/code_app/views/terminal/consumer.py"""

import pytest

# from apps.code_app.views.terminal.consumer import ...


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
# Start of Source Code from: apps/code_app/views/terminal/consumer.py
# --------------------------------------------------------------------------------
# """
# Real PTY Terminal for Code Workspace
# WebSocket-based interactive terminal with full PTY support
# 
# Architecture:
#     Django WebSocket → srun --pty → Apptainer shell → User workspace
# 
# Security:
#     - SLURM handles resource isolation (CPU, memory, time)
#     - Apptainer provides container isolation (no root, UID preserved)
#     - Filesystem quotas at OS level
#     - No Docker socket exposure
# 
# Resource Fairness:
#     - SLURM fair-share scheduling
#     - Per-user accounting
#     - express partition for interactive (priority)
#     - Configurable limits per partition
# 
# Maintainability:
#     - Single resource management system (SLURM)
#     - Same architecture for interactive + batch jobs
#     - Dev fallback when SLURM unavailable
# """
# 
# import asyncio
# import logging
# import os
# import pty
# import select
# import signal
# import termios
# 
# from channels.generic.websocket import AsyncWebsocketConsumer
# from apps.project_app.models import Project
# 
# from .config import USER_DATA_ROOT
# from .execution import (
#     is_slurm_available,
#     select_container,
#     exec_slurm_shell,
# )
# from .workspace import ensure_workspace
# 
# logger = logging.getLogger(__name__)
# 
# 
# class TerminalConsumer(AsyncWebsocketConsumer):
#     """
#     WebSocket consumer for PTY terminal.
# 
#     Spawns interactive shell via SLURM + Apptainer for:
#     - Security: Container isolation, no root access
#     - Fairness: SLURM scheduling, per-user limits
#     - Consistency: Same architecture dev/prod/HPC
#     """
# 
#     async def connect(self):
#         """Accept WebSocket connection and spawn PTY"""
#         self.user = self.scope['user']
#         self.pid = None
#         self.fd = None
#         self.reader_task = None
# 
#         # Get project ID from query params
#         query_params = dict(
#             (x.split('=') for x in self.scope['query_string'].decode().split('&') if '=' in x)
#         )
#         project_id = query_params.get('project_id')
# 
#         if not project_id:
#             await self.close()
#             return
# 
#         try:
#             self.project = await asyncio.to_thread(
#                 Project.objects.select_related('owner').get,
#                 id=project_id
#             )
# 
#             # Check permissions
#             if self.user.is_authenticated:
#                 has_access = (
#                     self.user == self.project.owner or
#                     await asyncio.to_thread(
#                         lambda: self.user in self.project.collaborators.all()
#                     )
#                 )
#             else:
#                 # For visitors, check allocated project
#                 session = self.scope.get('session', {})
#                 visitor_project_id = session.get('visitor_project_id')
#                 has_access = (visitor_project_id and int(project_id) == visitor_project_id)
# 
#             if not has_access:
#                 await self.close()
#                 return
# 
#         except Project.DoesNotExist:
#             await self.close()
#             return
# 
#         await self.accept()
#         await self.spawn_pty()
# 
#     async def spawn_pty(self):
#         """Spawn PTY via SLURM + Apptainer (with dev fallback)"""
#         username = self.project.owner.username
#         project_slug = self.project.slug
# 
#         # User workspace paths
#         user_data_dir = USER_DATA_ROOT / username
#         project_dir = user_data_dir / "proj" / project_slug
# 
#         # Ensure directories exist
#         await ensure_workspace(user_data_dir, username, project_slug)
# 
#         # Select container (priority: project → user → base)
#         container_path = await asyncio.to_thread(
#             select_container, user_data_dir, project_dir
#         )
# 
#         # Check if SLURM is available
#         use_slurm = await asyncio.to_thread(is_slurm_available)
# 
#         # Block signals during PTY fork to prevent "Interrupted system call" errors
#         # This is a known SLURM issue (SchedMD Bug #3979) where signals can
#         # interrupt the accept() call during PTY setup
#         old_mask = signal.pthread_vissk(
#             signal.SIG_BLOCK,
#             {signal.SIGCHLD, signal.SIGWINCH, signal.SIGINT, signal.SIGTERM}
#         )
# 
#         try:
#             # Create PTY
#             self.pid, self.fd = pty.fork()
# 
#             if self.pid == 0:
#                 # Child process - restore signal mask before exec
#                 signal.pthread_vissk(signal.SIG_SETMASK, old_mask)
#                 if use_slurm:
#                     exec_slurm_shell(username, user_data_dir, project_dir, container_path, project_slug)
#                 else:
#                     # SECURITY: No fallback - SLURM is required for all terminals
#                     logger.error("SLURM not available - terminals disabled for security")
#                     os._exit(1)
#         finally:
#             # Parent process - restore signal mask
#             if self.pid != 0:
#                 signal.pthread_vissk(signal.SIG_SETMASK, old_mask)
# 
#         # Parent process - read from PTY
#         if self.pid != 0:
#             self.reader_task = asyncio.create_task(self.read_pty())
# 
#     async def read_pty(self):
#         """Read from PTY and send to WebSocket"""
#         try:
#             while True:
#                 r, _, _ = await asyncio.to_thread(
#                     select.select, [self.fd], [], [], 0.1
#                 )
# 
#                 if r:
#                     try:
#                         data = await asyncio.to_thread(os.read, self.fd, 4096)
#                         if data:
#                             await self.send(text_data=data.decode('utf-8', errors='replace'))
#                         else:
#                             break  # EOF
#                     except OSError:
#                         break
#         except Exception as e:
#             logger.error(f"PTY read error: {e}")
#         finally:
#             await self.close()
# 
#     async def receive(self, text_data):
#         """Receive data from WebSocket and write to PTY"""
#         try:
#             if text_data.startswith('resize:'):
#                 _, rows, cols = text_data.split(':')
#                 await self.resize_pty(int(rows), int(cols))
#             else:
#                 await asyncio.to_thread(os.write, self.fd, text_data.encode('utf-8'))
#         except Exception as e:
#             logger.error(f"PTY write error: {e}")
# 
#     async def resize_pty(self, rows: int, cols: int):
#         """Resize PTY window"""
#         try:
#             # tcsetwinsize expects a two-item tuple (rows, cols)
#             await asyncio.to_thread(termios.tcsetwinsize, self.fd, (rows, cols))
#         except Exception as e:
#             logger.error(f"PTY resize error: {e}")
# 
#     async def disconnect(self, close_code):
#         """Clean up on disconnect"""
#         if self.reader_task:
#             self.reader_task.cancel()
# 
#         if self.pid and self.pid > 0:
#             try:
#                 os.kill(self.pid, 9)
#             except ProcessLookupError:
#                 pass
# 
#         if self.fd:
#             try:
#                 os.close(self.fd)
#             except OSError:
#                 pass
# 
# 
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/code_app/views/terminal/consumer.py
# --------------------------------------------------------------------------------
