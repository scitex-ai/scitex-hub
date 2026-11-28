#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/api.py
"""Django API tools for FastMCP server."""

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Optional

# ── On-site auth (HMAC) ────────────────────────────────────────────────
# Canonical, single-source signing AND verification primitives, used by
# BOTH the MCP client (this module, the sender — see
# ``_build_auth_headers``) and the Django ``OnSiteAuthMiddleware``
# (the verifier, ``apps/infra/project_app/middleware_onsite_auth.py``,
# which calls ``verify_onsite`` from here). Keeping signer and verifier
# in one module is what makes them unable to drift.
#
# This replaces the previous plaintext-username-plus-internal-IP model,
# in which any request could forge ``X-SciTeX-OnSite: <username>`` and be
# authenticated as that user. That IP check was not a boundary at all:
# the middleware derived the "client IP" from
# ``X-Forwarded-For.split(",")[0]`` — the leftmost element, which is
# exactly the part the CLIENT writes (nginx *appends* the real peer via
# ``$proxy_add_x_forwarded_for``), so a public request carrying
# ``X-Forwarded-For: 127.0.0.1`` passed it. A signature made with the
# claimed user's own derived key (``derive_onsite_key``) is now the only
# trust signal; the master secret itself is never handed to agents.
ONSITE_USER_HEADER = "X-SciTeX-OnSite"
ONSITE_SIG_HEADER = "X-SciTeX-OnSite-Sig"
ONSITE_TS_HEADER = "X-SciTeX-OnSite-Ts"
ONSITE_EPOCH_HEADER = "X-SciTeX-OnSite-Key-Epoch"

# Env var carrying the server's MASTER on-site secret (read into Django
# settings as ``ONSITE_AUTH_SECRET``). The master never leaves the server:
# it is not written into any user-visible file and is stripped from the
# environment of user shells. Agents receive only a per-user key derived
# from it (``derive_onsite_key``), which cannot sign for anyone else.
ONSITE_SECRET_ENV = "SCITEX_HUB_ONSITE_SECRET"

# Env vars carrying the per-user derived key and its issue epoch inside a
# user's terminal session (see ``issue_onsite_credentials``).
ONSITE_KEY_ENV = "SCITEX_HUB_ONSITE_KEY"
ONSITE_KEY_EPOCH_ENV = "SCITEX_HUB_ONSITE_KEY_EPOCH"

# Audience / version tag bound into both the key derivation and every
# signed request, so these keys cannot be replayed into another HMAC use
# of the same master.
ONSITE_AUDIENCE = "scitex-hub-onsite-v2"

# Replay window for a single request, seconds.
ONSITE_MAX_SKEW_SECONDS = 300

# Key lifetime: a derived key is bound to the day it was issued and is
# refused once it is older than ``ONSITE_KEY_MAX_AGE_DAYS``. Every new
# terminal session is issued a fresh key.
ONSITE_KEY_PERIOD_SECONDS = 86400
ONSITE_KEY_MAX_AGE_DAYS = 14


def current_key_epoch(now: Optional[float] = None) -> int:
    """Issue epoch (whole days since the Unix epoch) for a new key."""
    return int((time.time() if now is None else now) // ONSITE_KEY_PERIOD_SECONDS)


def derive_onsite_key(master: str, username: str, epoch: int) -> str:
    """Per-user on-site key: ``HMAC(master, audience|username|epoch)``.

    Holding this key lets an agent sign requests for ``username`` only,
    and only until the key ages out; it reveals nothing about the master.
    """
    message = f"{ONSITE_AUDIENCE}|key|{username}|{int(epoch)}"
    return hmac.new(
        master.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def onsite_message(username: str, epoch: int, timestamp: str) -> str:
    """Canonical signing payload for an on-site request."""
    return f"{ONSITE_AUDIENCE}|req|{username}|{int(epoch)}|{timestamp}"


def sign_onsite(username: str, epoch: int, timestamp: str, key: str) -> str:
    """HMAC-SHA256 hex digest binding a request to (username, epoch, ts).

    ``key`` is the PER-USER derived key, never the master. ``timestamp``
    is signed as the exact string transmitted on the wire so the verifier
    can recompute it without any normalization ambiguity.
    """
    return hmac.new(
        key.encode("utf-8"),
        onsite_message(username, epoch, timestamp).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def wsgi_meta_key(header: str) -> str:
    """``X-SciTeX-OnSite-Sig`` -> ``HTTP_X_SCITEX_ONSITE_SIG``.

    Derived from the header constants so the verifier can never read a
    different header than the signer writes.
    """
    return "HTTP_" + header.upper().replace("-", "_")


def verify_onsite(
    meta,
    master: str,
    now: Optional[float] = None,
    max_skew: int = ONSITE_MAX_SKEW_SECONDS,
    max_key_age_days: int = ONSITE_KEY_MAX_AGE_DAYS,
) -> Optional[str]:
    """Verify on-site auth headers; return the username, or ``None``.

    The verifier re-derives the key for the CLAIMED username from the
    master, so a key issued to one user can never authenticate another.
    Returns the username ONLY when the request carries a fresh, correctly
    signed header set with a key that has not aged out. Every failure path
    returns ``None`` (fail closed), including an empty ``master``.
    """
    if not master:
        return None

    username = meta.get(wsgi_meta_key(ONSITE_USER_HEADER))
    signature = meta.get(wsgi_meta_key(ONSITE_SIG_HEADER))
    timestamp = meta.get(wsgi_meta_key(ONSITE_TS_HEADER))
    epoch_raw = meta.get(wsgi_meta_key(ONSITE_EPOCH_HEADER))
    if not username or not signature or not timestamp or not epoch_raw:
        return None

    try:
        issued_at = float(timestamp)
        epoch = int(epoch_raw)
    except (TypeError, ValueError):
        return None

    reference = time.time() if now is None else now
    if abs(reference - issued_at) > max_skew:
        return None
    age_days = current_key_epoch(reference) - epoch
    if age_days < 0 or age_days > max_key_age_days:
        return None

    key = derive_onsite_key(master, username, epoch)
    expected = sign_onsite(username, epoch, timestamp, key)
    if not hmac.compare_digest(expected, signature):
        return None

    return username


def issue_onsite_credentials(
    username: str, master: Optional[str] = None, now: Optional[float] = None
) -> dict[str, str]:
    """Per-user on-site credentials for ONE terminal session's environment.

    Returns ``{}`` when no master is configured (on-site auth disabled) or
    no username is given. The result is meant for a process environment,
    never for a file in the user's project or home directory.
    """
    master = os.environ.get(ONSITE_SECRET_ENV, "") if master is None else master
    if not master or not username:
        return {}
    epoch = current_key_epoch(now)
    return {
        ONSITE_KEY_ENV: derive_onsite_key(master, username, epoch),
        ONSITE_KEY_EPOCH_ENV: str(epoch),
    }


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def _resolve_user_token() -> Optional[str]:
    """Resolve the caller's personal `scitex_xxxx` PAT.

    Resolution order (Phase-1 card #5 — MCP tools authenticate as the
    user, not as the server's TOOL_TOKEN):

    1. ``SCITEX_HUB_TOKEN`` env var (explicit, dev-friendly).
    2. ``~/.scitex/cloud/runtime/token.json`` cache produced by
       ``scitex-hub account token create`` (PR #274). Looks at the
       ``access`` key — same shape the CLI writes.

    Returns ``None`` if neither source yields a token. Caller is
    responsible for the back-compat fall-through to TOOL_TOKEN
    (``SCITEX_HUB_API_KEY``).
    """
    env_tok = os.environ.get("SCITEX_HUB_TOKEN")
    if env_tok:
        return env_tok

    # File cache — same canonical path the CLI writes (PR #274).
    try:
        from scitex_config._ecosystem import local_state

        cache = local_state.runtime_path("cloud", "token.json")
    except Exception:
        cache = Path.home() / ".scitex" / "cloud" / "runtime" / "token.json"

    try:
        if cache.exists():
            data = json.loads(cache.read_text())
            tok = data.get("access")
            if tok:
                return str(tok)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def get_on_site_env(username: str = "", site_url: str = "") -> dict[str, str]:
    """Build the NON-SECRET env vars for on-site MCP (written to .mcp.json).

    Args:
        username: The container user's Django username.
        site_url: Django server URL. Falls back to SCITEX_HUB_SITE_URL env
                  var, then to http://web:8000 (Docker internal).

    No credential is ever included: these values end up in files inside
    the user's project. The per-user signing key reaches the agent through
    the terminal session's environment (``issue_onsite_credentials``).
    """
    url = site_url or os.environ.get("SCITEX_HUB_SITE_URL", "http://web:8000")
    env = {"SCITEX_HUB_IS_ON_SITE": "1", "SCITEX_HUB_URL": url}
    if username:
        env["SCITEX_HUB_USERNAME"] = username
    return env


def _get_config() -> dict:
    """Get API configuration from environment."""
    is_on_site = os.environ.get("SCITEX_HUB_IS_ON_SITE") == "1"
    return {
        "api_key": os.environ.get("SCITEX_HUB_API_KEY"),
        "base_url": os.environ.get(
            "SCITEX_HUB_URL",
            "http://web:8000" if is_on_site else "https://scitex.ai",
        ),
        "is_on_site": is_on_site,
        "username": os.environ.get("SCITEX_HUB_USERNAME", ""),
        "onsite_key": os.environ.get(ONSITE_KEY_ENV, ""),
        "onsite_key_epoch": os.environ.get(ONSITE_KEY_EPOCH_ENV, ""),
    }


def onsite_headers(
    username: str, key: str, epoch: int, now: Optional[float] = None
) -> dict:
    """Signed on-site auth headers for one outbound request."""
    timestamp = str(int(time.time() if now is None else now))
    return {
        ONSITE_USER_HEADER: username,
        ONSITE_TS_HEADER: timestamp,
        ONSITE_EPOCH_HEADER: str(int(epoch)),
        ONSITE_SIG_HEADER: sign_onsite(username, epoch, timestamp, key),
    }


def _build_auth_headers(config: dict, auth_required: bool) -> dict[str, str]:
    """Compute the headers ``_make_request`` sends for one call.

    Pulled out as a pure function (config-in / headers-out) so it is
    directly testable without rewiring the HTTP transport — the test
    asserts the chosen ``Authorization`` value, not the network call.

    Auth precedence (card #5):
      1. On-site HMAC-signed headers (dev/cluster path), signed with the
         session's PER-USER derived key. Without that key no on-site header
         is sent at all (an unsigned one is not an authenticator).
      2. User PAT — SCITEX_HUB_TOKEN env, then ~/.scitex/cloud/runtime/token.json.
      3. Back-compat: server-side TOOL_TOKEN exposed as SCITEX_HUB_API_KEY.
    If none of the above resolve, raise — never send anonymous when
    ``auth_required`` is True.
    """
    headers = {"X-Requested-With": "XMLHttpRequest"}
    if not auth_required:
        return headers
    if config["is_on_site"] and config["username"]:
        key = config.get("onsite_key") or ""
        epoch = config.get("onsite_key_epoch") or ""
        if key and epoch.isdigit():
            headers.update(onsite_headers(config["username"], key, int(epoch)))
            return headers
        # No per-user on-site key in this session: fall through to the
        # user's own token rather than sending a forgeable plaintext header.
    user_token = _resolve_user_token()
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
        return headers
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
        return headers
    raise RuntimeError(
        "no hub credential available — set SCITEX_HUB_TOKEN, "
        "run `scitex-hub account token create`, or set "
        "SCITEX_HUB_API_KEY (back-compat TOOL_TOKEN)."
    )


def _make_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    auth_required: bool = True,
) -> dict:
    """Make HTTP request to SciTeX Hub API."""
    import requests

    config = _get_config()
    url = f"{config['base_url']}{endpoint}"

    headers = _build_auth_headers(config, auth_required)

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=60)
        elif method.upper() == "POST":
            if files:
                response = requests.post(
                    url, headers=headers, data=data, files=files, timeout=120
                )
            else:
                response = requests.post(url, headers=headers, json=data, timeout=60)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"success": False, "error": f"Unknown method: {method}"}

        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            result = response.json()
            result["success"] = True
            return result
        except json.JSONDecodeError:
            return {"success": True, "content": response.text}

    except requests.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.ConnectionError:
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_api_tools(mcp) -> None:
    """Register Django API tools with FastMCP server."""

    @mcp.tool()
    async def api_scholar_search(
        query: str,
        limit: int = 10,
    ) -> str:
        """Use whenever the user asks to search papers, find publications, look up scholarly articles, or mentions the SciTeX Hub scholar database; replaces raw HTTP calls to the SciTeX Hub /api/v1/scholar/search/ REST endpoint (public, no auth)."""
        result = _make_request(
            "GET",
            "/api/v1/scholar/search/",
            data={"q": query, "limit": limit},
            auth_required=False,
        )
        return _json(result)

    @mcp.tool()
    async def api_crossref_search(
        query: str,
        rows: int = 10,
        offset: int = 0,
    ) -> str:
        """Use when the user asks to search CrossRef, lookup DOI metadata by query, or enrich a bibliography via the SciTeX Hub CrossRef proxy; replaces raw HTTP calls to the SciTeX Hub /scholar/api/crossref/search/ REST endpoint (auth required)."""
        result = _make_request(
            "GET",
            "/scholar/api/crossref/search/",
            data={"query": query, "rows": rows, "offset": offset},
        )
        return _json(result)

    @mcp.tool()
    async def api_crossref_by_doi(doi: str) -> str:
        """Use when the user asks to resolve a DOI, fetch CrossRef metadata for a specific DOI, or verify a citation via SciTeX Hub; replaces raw HTTP calls to the SciTeX Hub /scholar/api/crossref/doi/ REST endpoint."""
        result = _make_request(
            "GET",
            "/scholar/api/crossref/doi/",
            data={"doi": doi},
        )
        return _json(result)

    @mcp.tool()
    async def api_writer_compile(
        project_id: str,
        document_type: str = "manuscript",
    ) -> str:
        """Use when the user asks to compile a LaTeX manuscript, build a PDF, or render a writer project on SciTeX Hub; replaces raw HTTP calls to the SciTeX Hub /writer/api/compile/ REST endpoint. Document types: manuscript, supplementary, revision."""
        result = _make_request(
            "POST",
            "/writer/api/compile/",
            data={"project_id": project_id, "document_type": document_type},
        )
        return _json(result)

    @mcp.tool()
    async def api_writer_list_sections(project_id: str) -> str:
        """Use when the user asks to list manuscript sections, inspect writer project structure, or see chapter layout on SciTeX Hub; replaces raw HTTP calls to the SciTeX Hub /writer/api/sections/ REST endpoint."""
        result = _make_request(
            "GET",
            "/writer/api/sections/",
            data={"project_id": project_id},
        )
        return _json(result)

    @mcp.tool()
    async def api_project_list_files(
        project_id: str,
        path: str = "",
    ) -> str:
        """Use when the user asks to list files, browse a directory, or inspect the tree of a SciTeX Hub project; replaces raw HTTP calls to the SciTeX Hub /project/api/files/ REST endpoint."""
        result = _make_request(
            "GET",
            "/project/api/files/",
            data={"project_id": project_id, "path": path},
        )
        return _json(result)

    @mcp.tool()
    async def api_project_commit(
        project_id: str,
        message: str,
        files: Optional[list] = None,
    ) -> str:
        """Use when the user asks to commit changes, save edits, or snapshot a SciTeX Hub project to Git; replaces raw HTTP calls to the SciTeX Hub /project/api/commit/ REST endpoint. Pass files=[paths] to commit a subset, else all changes commit."""
        data = {"project_id": project_id, "message": message}
        if files:
            data["files"] = files
        result = _make_request("POST", "/project/api/commit/", data=data)
        return _json(result)

    @mcp.tool()
    async def api_enrich_bibtex(
        bibtex_content: str,
        use_cache: bool = True,
    ) -> str:
        """Use when the user asks to enrich a .bib file, fill in missing DOIs/abstracts/impact-factors, or run BibTeX enrichment via SciTeX Hub; replaces raw HTTP calls to the SciTeX Hub /scholar/bibtex/upload/ REST endpoint plus job polling."""
        import io
        import time

        # Upload file
        files = {"bibtex_file": ("input.bib", io.StringIO(bibtex_content))}
        data = {"use_cache": "true" if use_cache else "false"}

        upload_result = _make_request(
            "POST",
            "/scholar/bibtex/upload/",
            data=data,
            files=files,
        )

        if not upload_result.get("success"):
            return _json(upload_result)

        job_id = upload_result.get("job_id")
        if not job_id:
            return _json({"success": False, "error": "No job ID returned"})

        # Poll for completion
        config = _get_config()
        import requests

        max_attempts = 60
        for _ in range(max_attempts):
            # Single source of auth-header truth — this used to be a
            # second, hand-rolled copy that (like _build_auth_headers)
            # sent the forgeable plaintext on-site header. Rebuilt every
            # attempt so the on-site signature stays inside the replay
            # window during a long poll.
            headers = _build_auth_headers(config, auth_required=True)
            try:
                response = requests.get(
                    f"{config['base_url']}/scholar/api/bibtex/job/{job_id}/status/",
                    headers=headers,
                    timeout=30,
                )
                status_data = response.json()
                status = status_data.get("status")

                if status == "completed":
                    # Download result
                    download_response = requests.get(
                        f"{config['base_url']}/scholar/api/bibtex/job/{job_id}/download/",
                        headers=headers,
                        timeout=60,
                    )
                    if download_response.status_code == 200:
                        return _json(
                            {
                                "success": True,
                                "bibtex": download_response.text,
                                "job_id": job_id,
                            }
                        )
                    else:
                        return _json({"success": False, "error": "Download failed"})

                elif status in ("failed", "cancelled"):
                    return _json(
                        {"success": False, "error": f"Job {status}", "job_id": job_id}
                    )

                time.sleep(2)

            except Exception as e:
                return _json({"success": False, "error": str(e)})

        return _json({"success": False, "error": "Job timed out", "job_id": job_id})

    @mcp.tool()
    async def api_status() -> str:
        """Use when the user asks whether SciTeX Hub is up, to check API health, verify credentials, or debug a connection issue; replaces raw HTTP calls to the SciTeX Hub /api/v1/status/ REST endpoint."""
        config = _get_config()
        result = {
            "base_url": config["base_url"],
            "api_key_configured": bool(config["api_key"]),
        }

        # Try a simple health check
        try:
            import requests

            response = requests.get(
                f"{config['base_url']}/api/v1/status/",
                timeout=10,
            )
            result["cloud_status"] = (
                "online" if response.status_code == 200 else "error"
            )
            result["success"] = True
        except Exception as e:
            result["cloud_status"] = "unreachable"
            result["error"] = str(e)
            result["success"] = False

        return _json(result)


# EOF
