"""SSH key registration helpers for the SSH gateway.

Handles both interactive key paste and ssh-copy-id command parsing.
"""

import logging
import re

import paramiko

logger = logging.getLogger(__name__)


def register_ssh_key(user, public_key: str) -> tuple[bool, str]:
    """Validate and register an SSH public key for a user.

    Returns (success, message).
    """
    from apps.accounts_app.models import WorkspaceSSHKey
    from apps.accounts_app.utils.ssh_key_validator import SSHKeyValidator

    parsed = SSHKeyValidator.validate_and_parse(public_key)
    if not parsed["valid"]:
        return False, parsed["error"]

    fingerprint = parsed["fingerprint"]
    key_type = parsed["key_type"]

    if WorkspaceSSHKey.objects.filter(user=user, fingerprint=fingerprint).exists():
        return True, f"Key already registered ({fingerprint[:20]}...)"

    comment = parsed["comment"] or f"{key_type} key"
    title = comment[:100]

    WorkspaceSSHKey.objects.create(
        user=user,
        title=title,
        public_key=parsed["formatted_key"],
        fingerprint=fingerprint,
        key_type=key_type.replace("ssh-", ""),
    )
    logger.info(f"SSH key registered for {user.username}: {fingerprint[:20]}...")
    return True, fingerprint


def handle_ssh_copy_id(channel: paramiko.Channel, cmd_str: str, user):
    """Extract and register SSH key from ssh-copy-id exec command."""
    try:
        key_match = re.search(
            r"(ssh-(?:rsa|ed25519|dss|ecdsa\S*)\s+[A-Za-z0-9+/=]+(?:\s+\S+)?)",
            cmd_str,
        )
        if key_match:
            public_key = key_match.group(1).strip()
            success, msg = register_ssh_key(user, public_key)
            if success:
                channel.send(f"\r\nKey registered successfully: {msg}\r\n".encode())
            else:
                channel.send(f"\r\nKey registration failed: {msg}\r\n".encode())
        else:
            channel.send(
                b"\r\nCould not extract SSH key from command.\r\n"
                b"Register your key via /accounts/settings/ssh-keys/\r\n"
            )
        channel.send_exit_status(0)
        channel.close()
    except Exception as e:
        logger.error(f"ssh-copy-id handler error: {e}", exc_info=True)
        try:
            channel.send(f"\r\nError: {e}\r\n".encode())
            channel.send_exit_status(1)
            channel.close()
        except Exception:
            pass


def handle_password_session(channel: paramiko.Channel, user):
    """Interactive key registration for password-only auth sessions."""
    try:
        channel.send(
            b"\r\n"
            b"=== SciTeX Cloud SSH Key Registration ===\r\n"
            b"\r\n"
            b"Password authentication grants key registration only.\r\n"
            b"To get a full shell, register your SSH public key.\r\n"
            b"\r\n"
            b"Options:\r\n"
            b"  1. Paste your public key below\r\n"
            b"  2. Use: ssh-copy-id -p 2200 "
        )
        channel.send(f"{user.username}@<host>\r\n".encode())
        channel.send(
            b"  3. Register via web UI: /accounts/settings/ssh-keys/\r\n"
            b"\r\n"
            b"Paste your public key (or Ctrl+C to cancel):\r\n"
            b"> "
        )

        key_buf = b""
        while True:
            data = channel.recv(1)
            if not data:
                break
            if data == b"\x03":
                channel.send(b"\r\nCancelled.\r\n")
                break
            if data in (b"\r", b"\n"):
                channel.send(b"\r\n")
                key_str = key_buf.decode("utf-8", errors="replace").strip()
                if key_str:
                    success, msg = register_ssh_key(user, key_str)
                    if success:
                        channel.send(f"Key registered: {msg}\r\n".encode())
                        channel.send(
                            b"\r\nYou can now SSH with your key:\r\n  ssh -p 2200 "
                        )
                        channel.send(f"{user.username}@<host>\r\n\r\n".encode())
                    else:
                        channel.send(f"Error: {msg}\r\n".encode())
                break
            if data in (b"\x7f", b"\x08"):
                if key_buf:
                    key_buf = key_buf[:-1]
                    channel.send(b"\x08 \x08")
                continue
            key_buf += data
            channel.send(data)
    except Exception as e:
        logger.debug(f"Password session error: {e}")
    finally:
        try:
            channel.close()
        except Exception:
            pass


# EOF
