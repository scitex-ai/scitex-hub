"""The environment every user-facing process starts from.

Terminals, SLURM jobs and project services are started by server processes
(the terminal broker, Django, Celery) whose environment holds the platform's
own secrets: database and cache credentials, the Django secret key, API
tokens, payment keys. ``srun`` and ``sbatch`` export the caller's
environment to the job by default, and processes inside an Apptainer
instance share the host PID namespace, so anything in the launching
environment is readable by the user (``/proc/<pid>/environ``).

So a user process never inherits the server environment. It starts from
:func:`user_process_env`: a short ALLOWLIST of runtime variables copied from
the server environment, plus the values the caller adds explicitly (the
user's own derived on-site key, project variables, the user's own provider
settings).
"""

from __future__ import annotations

import os
import re
from typing import Mapping, Optional

#: Copied from the server environment when present.
PASSTHROUGH_NAMES = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LANGUAGE",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "TERM",
        "TMPDIR",
        # SLURM client configuration (location of slurm.conf), not a secret.
        "SLURM_CONF",
    }
)

#: Runtime configuration read by the container tooling itself. The
#: ``*ENV_`` forms are excluded: they inject variables INTO the container.
PASSTHROUGH_PREFIXES = ("APPTAINER_", "SINGULARITY_")
_INJECTING_PREFIXES = ("APPTAINERENV_", "SINGULARITYENV_")

#: Second gate on anything copied from the server environment.
SECRET_NAME_RE = re.compile(
    r"(SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|APIKEY|PRIVATE|CREDENTIAL|DSN|"
    r"AUTH|COOKIE|SESSION|^STRIPE_|^AWS_|^DATABASE_URL$|^REDIS_URL$)",
    re.IGNORECASE,
)


def _passthrough(name: str) -> bool:
    if SECRET_NAME_RE.search(name):
        return False
    if name in PASSTHROUGH_NAMES:
        return True
    if name.startswith(_INJECTING_PREFIXES):
        return False
    return name.startswith(PASSTHROUGH_PREFIXES)


def user_process_env(
    server_env: Optional[Mapping[str, str]] = None,
    *,
    username: str = "",
    extra: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    """Environment for a process that runs user code or a user session.

    ``server_env`` defaults to ``os.environ``; only allowlisted names are
    copied from it. When ``username`` is given and the on-site master is
    configured, the user's own derived on-site key is added (plain and
    ``APPTAINERENV_``-prefixed so it reaches the container on either exec
    path). ``extra`` is added last and is trusted: callers put only values
    that belong to this user there.
    """
    source = os.environ if server_env is None else server_env
    env = {k: v for k, v in source.items() if _passthrough(k)}
    env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    env.setdefault("LANG", "C.UTF-8")
    if username:
        from scitex_hub._mcp_tools.api import (
            ONSITE_SECRET_ENV,
            issue_onsite_credentials,
        )

        master = source.get(ONSITE_SECRET_ENV, "")
        for key, value in issue_onsite_credentials(username, master=master).items():
            env[key] = value
            env[f"APPTAINERENV_{key}"] = value
    if extra:
        env.update(extra)
    return env
