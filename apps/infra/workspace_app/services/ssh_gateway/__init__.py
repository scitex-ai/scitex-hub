"""SSH Gateway service package.

Architecture:
    SSH client -> paramiko Transport -> Terminal Broker (Unix socket)
    -> SLURM allocation + Apptainer (same path as the web terminal)

Authentication: public keys registered in the Hub only. Keys are managed at
/accounts/settings/ssh-keys/. Connections and failed logins are throttled
per source and per username (see throttle.py, docs/ops/ssh-gateway.md).
"""

from .broker_client import SyncBrokerClient
from .client_handler import handle_client
from .server_interface import SSHGateway
from .throttle import GatewayThrottle, ThrottleConfig

__all__ = [
    "GatewayThrottle",
    "SSHGateway",
    "SyncBrokerClient",
    "ThrottleConfig",
    "handle_client",
]

# EOF
