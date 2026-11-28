"""Validation and a guarded runner for tenant-supplied ``git clone`` sources.

A tenant can ask the server to import a project from a repository URL. ``git``
accepts far more than web URLs: local paths and ``file://`` URLs (which would
read another tenant's repository off the shared disk), ``ext::`` / other
transports, internal hosts (the platform's own services, cloud metadata,
RFC1918 ranges) and arguments that start with ``-`` (option injection). This
module narrows the input to what an import actually needs:

* ``https://<public host>/...`` — the host is resolved ONCE through
  :mod:`url_safety` and every address must be public. Redirects are resolved
  up front with :func:`url_safety.fetch_public_url` (every hop re-validated),
  and ``git`` is then pinned to the vetted address (``http.curloptResolve``)
  with redirects disabled, so neither DNS rebinding nor a late redirect can
  move the connection to an internal address.
* ``ssh`` (``git@host:owner/repo`` or ``ssh://git@host/owner/repo``) — only to
  a configured allowlist of well-known public forges.

:func:`run_git_clone` then runs ``git`` with transports restricted by both
``protocol.allow`` and ``GIT_ALLOW_PROTOCOL``, ``--`` before the URL, symlinks
checked out as plain files, a wall-clock timeout and an on-disk size cap.
"""

from __future__ import annotations

import ipaddress
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence
from urllib.parse import urlparse, urlunparse

from .url_safety import _resolve_public_addresses, fetch_public_url

DEFAULT_SSH_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org")
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_BYTES = 2 * 1024**3  # 2 GiB on disk
_PROBE_TIMEOUT_SECONDS = 20
_SIZE_POLL_SECONDS = 0.5

# Path part of a forge repository reference: owner/repo(.git), nested groups
# allowed. No leading '-', no '..', no whitespace or shell/URL metacharacters.
_REPO_PATH_RE = re.compile(r"^(?!-)(?!.*\.\.)[A-Za-z0-9._~/-]+$")
_SCP_LIKE_RE = re.compile(
    r"^(?P<user>[A-Za-z0-9._-]+)@(?P<host>[A-Za-z0-9.-]+):(?P<path>.+)$"
)


class GitSourceRejected(ValueError):
    """Raised when a clone source is not an allowed public repository."""


@dataclass(frozen=True)
class GitSource:
    """A validated clone source.

    ``url`` is what ``git`` is given. For https sources ``pin`` holds the
    ``host:port:address`` triple handed to ``http.curloptResolve`` so the
    connection goes to the address that was validated.
    """

    url: str
    protocol: str  # "https" or "ssh"
    host: str
    pin: Optional[str] = None


def _configured_ssh_hosts() -> tuple[str, ...]:
    try:
        from django.conf import settings

        hosts = getattr(settings, "SCITEX_HUB_GIT_IMPORT_SSH_HOSTS", None)
    except Exception:  # settings not configured (plain library use)
        hosts = None
    if not hosts:
        return DEFAULT_SSH_HOSTS
    return tuple(h.strip().lower() for h in hosts if h and h.strip())


def _setting(name: str, default: int) -> int:
    try:
        from django.conf import settings

        return int(getattr(settings, name, default))
    except Exception:
        return default


def _reject_basic(raw: str) -> str:
    if not isinstance(raw, str):
        raise GitSourceRejected("repository URL must be text")
    url = raw.strip()
    if not url:
        raise GitSourceRejected("repository URL is empty")
    if url.startswith("-"):
        raise GitSourceRejected("repository URL may not start with '-'")
    if any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in url):
        raise GitSourceRejected(
            "repository URL contains whitespace or control characters"
        )
    return url


def _check_repo_path(path: str) -> None:
    path = path.lstrip("/")
    if not path or not _REPO_PATH_RE.match(path):
        raise GitSourceRejected("repository path is not a plain owner/name path")


def _ssh_source(url: str, ssh_hosts: Iterable[str]) -> GitSource:
    allowed = {h.lower() for h in ssh_hosts}
    if url.startswith("ssh://"):
        parsed = urlparse(url)
        user, host, path = parsed.username, (parsed.hostname or ""), parsed.path
        if parsed.password:
            raise GitSourceRejected("credentials may not be embedded in the URL")
    else:
        match = _SCP_LIKE_RE.match(url)
        if not match:
            raise GitSourceRejected("not a recognised ssh repository reference")
        user, host, path = match["user"], match["host"], match["path"]
    host = host.lower()
    if user not in (None, "git"):
        raise GitSourceRejected("ssh imports must use the 'git' user")
    if host not in allowed:
        raise GitSourceRejected(
            f"ssh imports are limited to {', '.join(sorted(allowed))}"
        )
    _check_repo_path(path)
    return GitSource(url=url, protocol="ssh", host=host)


def _pin_for(host: str, port: int, resolver) -> str:
    addresses = resolver(host, port)
    ip = addresses[0][1]
    if ipaddress.ip_address(ip).version == 6:
        ip = f"[{ip}]"
    return f"{host}:{port}:{ip}"


def _https_parts(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise GitSourceRejected("only https:// repository URLs are allowed")
    if parsed.username or parsed.password:
        raise GitSourceRejected("credentials may not be embedded in the URL")
    if parsed.query or parsed.fragment:
        raise GitSourceRejected("repository URL may not carry a query or fragment")
    host = (parsed.hostname or "").lower()
    if not host:
        raise GitSourceRejected("repository URL has no host")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise GitSourceRejected(f"invalid port: {exc}") from exc
    _check_repo_path(parsed.path)
    return parsed, host, port


def _follow_redirects(url: str, resolver, connector) -> str:
    """Return the repository URL after the forge's redirects.

    Smart-HTTP clients start at ``<repo>/info/refs?service=git-upload-pack``
    and adopt the redirected base, so this probes the same endpoint with the
    SSRF-safe fetcher: each hop is resolved, validated and pinned. The final
    hop must still be https.
    """
    probe = url.rstrip("/") + "/info/refs?service=git-upload-pack"
    try:
        resp = fetch_public_url(
            probe,
            timeout=_PROBE_TIMEOUT_SECONDS,
            headers={"User-Agent": "git/2 (scitex-hub import check)"},
            _resolver=resolver,
            _connector=connector,
        )
    except ValueError as exc:
        raise GitSourceRejected(str(exc)) from exc
    except Exception as exc:  # network failure: surface as a refusal
        raise GitSourceRejected(f"repository host is not reachable: {exc}") from exc
    try:
        final = resp.url or probe
    finally:
        resp.close()
        session = getattr(resp, "_ssrf_session", None)
        if session is not None:
            session.close()
    parsed = urlparse(final)
    suffix = "/info/refs"
    path = parsed.path[: -len(suffix)] if parsed.path.endswith(suffix) else parsed.path
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def validate_git_source(
    raw_url: str,
    *,
    ssh_hosts: Optional[Sequence[str]] = None,
    https_hosts: Optional[Sequence[str]] = None,
    follow_redirects: bool = True,
    _resolver=None,
    _connector=None,
) -> GitSource:
    """Validate a tenant-supplied clone source; raise :class:`GitSourceRejected`.

    ``https_hosts`` optionally restricts https sources to exact host names
    (checked before any network access and again after redirects).
    ``_resolver`` / ``_connector`` are the same dependency-injection seams that
    :func:`url_safety.fetch_public_url` exposes for tests.
    """
    url = _reject_basic(raw_url)
    hosts = tuple(ssh_hosts) if ssh_hosts is not None else _configured_ssh_hosts()
    if url.startswith("ssh://") or ("://" not in url and _SCP_LIKE_RE.match(url)):
        return _ssh_source(url, hosts)
    if "://" not in url:
        raise GitSourceRejected(
            "use an https:// URL (local paths and other forms are not accepted)"
        )

    resolver = _resolver if _resolver is not None else _resolve_public_addresses
    https_allowed = (
        {h.lower() for h in https_hosts} if https_hosts is not None else None
    )
    _parsed, host, port = _https_parts(url)
    if https_allowed is not None and host not in https_allowed:
        raise GitSourceRejected(f"host {host!r} is not an accepted repository host")
    try:
        resolver(host, port)
    except ValueError as exc:
        raise GitSourceRejected(str(exc)) from exc

    if follow_redirects:
        url = _follow_redirects(url, resolver, _connector)
        _parsed, host, port = _https_parts(url)
        if https_allowed is not None and host not in https_allowed:
            raise GitSourceRejected(f"redirect left the accepted hosts ({host!r})")

    try:
        pin = _pin_for(host, port, resolver)
    except ValueError as exc:
        raise GitSourceRejected(str(exc)) from exc
    return GitSource(url=url, protocol="https", host=host, pin=pin)


def _tree_size(root: Path, limit: int) -> int:
    total = 0
    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except FileNotFoundError:
                        continue
                    if total > limit:
                        return total
        except FileNotFoundError:
            continue
    return total


def git_clone_command(
    source: GitSource,
    dest: Path,
    *,
    extra_args: Sequence[str] = (),
    protocols: Optional[Sequence[str]] = None,
) -> list[str]:
    """Build the ``git clone`` argv for a validated source."""
    allowed = tuple(protocols) if protocols is not None else (source.protocol,)
    cmd = ["git", "-c", "protocol.allow=never"]
    for proto in allowed:
        cmd += ["-c", f"protocol.{proto}.allow=always"]
    cmd += [
        "-c",
        "core.symlinks=false",
        "-c",
        "submodule.recurse=false",
        "-c",
        "http.followRedirects=false",
    ]
    if source.pin:
        cmd += ["-c", f"http.curloptResolve={source.pin}"]
    cmd += [
        "clone",
        "--no-recurse-submodules",
        *extra_args,
        "--",
        source.url,
        str(dest),
    ]
    return cmd


def run_git_clone(
    source: GitSource,
    dest: Path,
    *,
    env: Optional[dict] = None,
    extra_args: Sequence[str] = (),
    timeout: Optional[float] = None,
    max_bytes: Optional[int] = None,
    protocols: Optional[Sequence[str]] = None,
) -> tuple[bool, str]:
    """Clone ``source`` into ``dest`` (absent or an empty directory).

    Returns ``(True, "")`` or ``(False, reason)``. The clone is killed and
    ``dest`` removed when it exceeds ``timeout`` seconds or ``max_bytes`` on
    disk. ``protocols`` overrides the transport allowlist; production callers
    leave it unset so only the source's own validated transport is enabled.
    """
    timeout = timeout or _setting(
        "SCITEX_HUB_GIT_IMPORT_TIMEOUT", DEFAULT_TIMEOUT_SECONDS
    )
    max_bytes = max_bytes or _setting(
        "SCITEX_HUB_GIT_IMPORT_MAX_BYTES", DEFAULT_MAX_BYTES
    )
    allowed = tuple(protocols) if protocols is not None else (source.protocol,)

    run_env = dict(env if env is not None else os.environ)
    run_env["GIT_ALLOW_PROTOCOL"] = ":".join(allowed)
    run_env["GIT_PROTOCOL_FROM_USER"] = "0"
    run_env["GIT_TERMINAL_PROMPT"] = "0"
    run_env.pop("GIT_CONFIG_PARAMETERS", None)
    run_env.pop("GIT_CONFIG_COUNT", None)

    cmd = git_clone_command(source, dest, extra_args=extra_args, protocols=allowed)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        env=run_env,
        text=True,
    )
    deadline = time.monotonic() + timeout
    failure = ""
    while proc.poll() is None:
        if time.monotonic() > deadline:
            failure = f"clone timed out (limit {int(timeout)} s)"
        elif dest.exists() and _tree_size(dest, max_bytes) > max_bytes:
            failure = f"repository exceeds the import size limit ({max_bytes} bytes)"
        if failure:
            proc.kill()
            break
        time.sleep(_SIZE_POLL_SECONDS)
    _out, err = proc.communicate()
    if not failure and proc.returncode == 0 and dest.exists():
        if _tree_size(dest, max_bytes) > max_bytes:
            failure = f"repository exceeds the import size limit ({max_bytes} bytes)"
        else:
            return True, ""
    if not failure:
        failure = (err or "").strip()[-2000:] or f"git clone exited {proc.returncode}"
    shutil.rmtree(dest, ignore_errors=True)
    return False, failure


def clone_tenant_source(
    raw_url: str,
    dest: Path,
    *,
    env: Optional[dict] = None,
    extra_args: Sequence[str] = (),
    timeout: Optional[float] = None,
) -> tuple[bool, str]:
    """Validate ``raw_url`` and clone it into ``dest``: the one entry point
    request handlers use."""
    try:
        source = validate_git_source(raw_url)
    except GitSourceRejected as exc:
        return False, f"Repository URL not accepted: {exc}"
    return run_git_clone(source, dest, env=env, extra_args=extra_args, timeout=timeout)
