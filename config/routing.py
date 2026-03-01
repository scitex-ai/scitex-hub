"""
WebSocket routing configuration for SciTeX Cloud.
"""

import scitex as stx
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import apps.console_app.routing
import apps.llm_app.routing
import apps.project_app.routing
import apps.writer_app.routing

application = ProtocolTypeRouter(
    {
        # HTTP protocol
        "http": get_asgi_application(),
        # WebSocket protocol
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    [
                        *apps.writer_app.routing.websocket_urlpatterns,
                        *apps.console_app.routing.websocket_urlpatterns,
                        *apps.llm_app.routing.websocket_urlpatterns,
                        *apps.project_app.routing.websocket_urlpatterns,
                    ]
                )
            )
        ),
    }
)


@stx.module
def main():
    """WebSocket routing configuration — not executed directly."""
    return 0


if __name__ == "__main__":
    main()
