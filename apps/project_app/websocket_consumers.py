#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Consumers for Project App

Handles WebSocket proxying to localhost services.
"""

import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ValidationError
import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)


class PortProxyWebSocketConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for proxying connections to localhost services.

    Used for services like Jupyter, VS Code Server, Streamlit that require
    WebSocket connections to function properly.

    URL: ws://{host}/{username}/{project}/ws/?port={port}
    """

    MIN_PORT = 10000
    MAX_PORT = 20000

    async def connect(self):
        """Handle WebSocket connection from client."""
        # Get username and slug from URL route
        self.username = self.scope["url_route"]["kwargs"].get("username")
        self.slug = self.scope["url_route"]["kwargs"].get("slug")
        self.user = self.scope.get("user")

        # Check authentication and project access
        if not self.user or not self.user.is_authenticated:
            logger.warning(f"Unauthenticated WebSocket connection attempt to {self.username}/{self.slug}")
            await self.close(code=4401)  # Unauthorized
            return

        # Check project access (similar to @project_access_required decorator)
        try:
            from apps.project_app.models import Project
            self.project = await Project.objects.select_related('owner').aget(
                owner__username=self.username,
                slug=self.slug
            )

            # Check if user has access
            has_access = (
                self.project.owner_id == self.user.id or
                self.project.is_public or
                await self.project.collaborators.filter(id=self.user.id).aexists()
            )

            if not has_access:
                logger.warning(f"User {self.user.username} denied access to {self.username}/{self.slug}")
                await self.close(code=4403)  # Forbidden
                return

        except Project.DoesNotExist:
            logger.warning(f"Project not found: {self.username}/{self.slug}")
            await self.close(code=4404)  # Not found
            return

        # Get port from query string
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        port = None

        for param in query_string.split('&'):
            if param.startswith('port='):
                try:
                    port = int(param.split('=')[1])
                except (ValueError, IndexError):
                    await self.close(code=4400)  # Bad request
                    return

        if not port:
            logger.warning("WebSocket connection without port parameter")
            await self.close(code=4400)
            return

        # Validate port
        try:
            self.validate_port(port)
        except ValidationError as e:
            logger.warning(f"Invalid port {port}: {e}")
            await self.close(code=4403)  # Forbidden
            return

        self.port = port

        # Build target URI - forward to root path of target service
        # Services like Jupyter run on their own ports and don't need our project path
        self.target_uri = f"ws://127.0.0.1:{port}/"

        # Preserve query string except for port parameter
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        if query_string:
            params = [p for p in query_string.split('&') if not p.startswith('port=')]
            if params:
                self.target_uri += '?' + '&'.join(params)

        logger.info(f"WebSocket proxy connecting to: {self.target_uri}")

        # Accept the WebSocket connection from client
        await self.accept()

        # Connect to target service
        try:
            logger.info(f"Attempting to connect to {self.target_uri}")

            # Note: extra_headers not supported in websockets 15.x
            # Headers will be passed through the WebSocket protocol naturally
            # Only pass subprotocols if they exist to avoid invalid empty header
            connect_kwargs = {'open_timeout': 10}
            subprotocols = self.scope.get('subprotocols')
            if subprotocols:
                connect_kwargs['subprotocols'] = subprotocols

            self.target_ws = await websockets.connect(
                self.target_uri,
                **connect_kwargs
            )

            logger.info(f"Successfully connected to {self.target_uri}")

            # Start forwarding messages
            self.forward_task = asyncio.create_task(self.forward_messages())

        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"Failed to connect to service on port {self.port}: {e}")
            await self.send(text_data=f"Error: Service not running on port {self.port}")
            await self.close(code=1011)  # Internal server error

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to service on port {self.port}")
            await self.send(text_data=f"Error: Timeout connecting to port {self.port}")
            await self.close(code=1011)

        except Exception as e:
            logger.error(f"Error connecting to WebSocket service: {e}", exc_info=True)
            await self.send(text_data=f"Error: {str(e)}")
            await self.close(code=1011)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        # Cancel forwarding task
        if hasattr(self, 'forward_task'):
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass

        # Close connection to target service
        if hasattr(self, 'target_ws'):
            try:
                await self.target_ws.close()
            except Exception as e:
                logger.debug(f"Error closing target WebSocket: {e}")

        logger.info(f"WebSocket proxy disconnected (port {self.port})")

    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive message from client and forward to target service.
        """
        if not hasattr(self, 'target_ws'):
            return

        try:
            if text_data:
                await self.target_ws.send(text_data)
            elif bytes_data:
                await self.target_ws.send(bytes_data)
        except WebSocketException as e:
            logger.error(f"Error sending to target service: {e}")
            await self.close(code=1011)
        except Exception as e:
            logger.error(f"Unexpected error in receive: {e}", exc_info=True)
            await self.close(code=1011)

    async def forward_messages(self):
        """
        Forward messages from target service to client.

        This runs as a background task, continuously listening for messages
        from the target service and forwarding them to the client.
        """
        try:
            async for message in self.target_ws:
                if isinstance(message, str):
                    await self.send(text_data=message)
                elif isinstance(message, bytes):
                    await self.send(bytes_data=message)
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except WebSocketException as e:
            logger.error(f"WebSocket error from target service: {e}")
            await self.close(code=1011)
        except Exception as e:
            logger.error(f"Error forwarding messages: {e}", exc_info=True)
            await self.close(code=1011)

    def validate_port(self, port: int) -> bool:
        """
        Validate port is in allowed range.

        Args:
            port: Port number to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If port is invalid
        """
        if not isinstance(port, int):
            raise ValidationError(f"Port must be an integer, got {type(port)}")

        if port < self.MIN_PORT or port > self.MAX_PORT:
            raise ValidationError(
                f"Port {port} is outside allowed range ({self.MIN_PORT}-{self.MAX_PORT})"
            )

        return True


# EOF
