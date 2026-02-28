"""SSH Gateway service package.

Architecture:
    SSH client → paramiko Transport → Terminal Broker (Unix socket) → SLURM+Apptainer

Auth flow:
    1. Password auth → key registration only (no shell)
    2. Public key auth → full shell via Terminal Broker
"""

from .broker_client import SyncBrokerClient
from .client_handler import handle_client
from .key_registration import register_ssh_key
from .server_interface import SSHGateway

__all__ = [
    "SSHGateway",
    "SyncBrokerClient",
    "handle_client",
    "register_ssh_key",
]

# EOF
