"""
ASGI config for SciTeX Cloud project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

# Use SCITEX_CLOUD_ prefix for configuration
settings_module = os.getenv("SCITEX_CLOUD_DJANGO_SETTINGS_MODULE") or "config.settings"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
django.setup()

# Import routing after Django setup
from apps.writer_app import routing as writer_routing
from apps.code_app import routing as code_routing
from apps.project_app import routing as project_routing

# Combine all WebSocket routes
websocket_urlpatterns = (
    writer_routing.websocket_urlpatterns +
    code_routing.websocket_urlpatterns +
    project_routing.websocket_urlpatterns
)

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
