"""
WebSocket routing configuration for SciTeX Cloud.
"""

import scitex as stx
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import apps.workspace.console_app.routing
import apps.infra.llm_app.routing
import apps.infra.platform_app.routing
import apps.infra.project_app.routing
import apps.workspace.writer_app.routing

application = ProtocolTypeRouter(
    {
        # HTTP protocol
        "http": get_asgi_application(),
        # WebSocket protocol
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    [
                        *apps.workspace.writer_app.routing.websocket_urlpatterns,
                        *apps.workspace.console_app.routing.websocket_urlpatterns,
                        *apps.infra.llm_app.routing.websocket_urlpatterns,
                        *apps.infra.platform_app.routing.websocket_urlpatterns,
                        *apps.infra.project_app.routing.websocket_urlpatterns,
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
