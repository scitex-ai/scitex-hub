#!/usr/bin/env python3
"""Read the resolved Compose contract without persisting environment secrets."""
import json
import os
import posixpath
import re
import shlex
import subprocess

from preflight_targets import APPS_MOUNTPOINT, TargetUnreachable

PYTHON_ROLES = ("django", "celery_worker", "celery_beat")
MODE_KEY = "SCITEX_APPS_PYTHON_MODE"


class DeploymentContext(object):
    def __init__(self, mode, image, apps_volume, roles):
        self.mode = mode
        self.image = image
        self.apps_volume = apps_volume
        self.roles = roles

    def summary(self):
        """Only non-secret policy/identity fields may leave this module."""
        return {"python_mode": self.mode, "image": self.image,
                "python_roles": list(self.roles), "apps_volume": self.apps_volume}


def _refuse(reason):
    raise TargetUnreachable("resolved Compose Python contract is unsafe: " + reason)


def _overlay_source(document, service):
    mounts = service.get("volumes", [])
    if not isinstance(mounts, list):
        _refuse("editable role volumes are not resolved")
    matches = [m for m in mounts if isinstance(m, dict) and m.get("target") == APPS_MOUNTPOINT]
    if len(matches) != 1:
        _refuse("editable mode needs one declared /app/.apps mount per Python role; direct-bind cohorts are not modelled by this gate")
    mount = matches[0]
    source = mount.get("source")
    if not isinstance(source, str) or not source:
        _refuse("editable apps mount has no source")
    if mount.get("type") == "volume":
        volumes = document.get("volumes", {})
        definition = volumes.get(source) if isinstance(volumes, dict) else None
        name = definition.get("name") if isinstance(definition, dict) else None
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            _refuse("editable apps volume has no resolved Docker name")
        return name
    if mount.get("type") == "bind" and source.startswith("/") and ":" not in source and "\x00" not in source:
        return source
    _refuse("editable apps mount is neither a resolved volume nor an absolute bind")


def parse_context(document):
    """Validate actual resolved role declarations, never the invoking shell mode."""
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        _refuse("services are missing")
    roles = {}
    for name in PYTHON_ROLES:
        service = document["services"].get(name)
        if not isinstance(service, dict):
            _refuse("a required Python role is missing")
        environment = service.get("environment")
        if not isinstance(environment, dict):
            _refuse("a Python role has no resolved environment")
        mode = environment.get(MODE_KEY)
        if mode not in ("image-only", "editable"):
            _refuse("every Python role must explicitly declare image-only or editable")
        image = service.get("image")
        if not isinstance(image, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,1023}", image):
            _refuse("a Python role has no valid resolved image")
        if mode == "image-only":
            entrypoint = service.get("entrypoint") or []
            entrypoint = [entrypoint] if isinstance(entrypoint, str) else entrypoint
            if not isinstance(entrypoint, list):
                _refuse("image-only entrypoint is not resolved")
            if any(isinstance(part, str) and "/docker_dev/entrypoint.sh" in part for part in entrypoint):
                _refuse("the direct development installer does not implement image-only mode")
            syspath = environment.get("PYTHONPATH")
            if syspath is not None and not isinstance(syspath, str):
                _refuse("image-only PYTHONPATH is not a resolved string")
            if any(posixpath.normpath(p) == APPS_MOUNTPOINT or posixpath.normpath(p).startswith(APPS_MOUNTPOINT + "/")
                   for p in (syspath or "").split(":")):
                _refuse("image-only Python cannot import from the frontend clone mount")
        roles[name] = {"mode": mode, "image": image, "service": service}
    modes = set(row["mode"] for row in roles.values())
    images = set(row["image"] for row in roles.values())
    if len(modes) != 1 or len(images) != 1:
        _refuse("Django, worker and beat must agree on Python mode and image")
    mode, image = modes.pop(), images.pop()
    apps_volume = None
    if mode == "editable":
        sources = set(_overlay_source(document, row["service"]) for row in roles.values())
        if len(sources) != 1:
            _refuse("editable Python roles disagree on the apps mount")
        apps_volume = sources.pop()
    return DeploymentContext(mode, image, apps_volume, PYTHON_ROLES)


def resolve_context(environment, repo_root, via_ssh=None, timeout=300):
    """Use precisely the sanctioned wrapper's env-file/overlay mapping.

    Compose's full JSON can contain secrets. Capture and parse it in memory;
    neither its stdout nor stderr is included in diagnostics or reports.
    ``--via-ssh`` requires this checkout path to exist on the target host too.
    """
    script = '''set -euo pipefail
source "$1/scripts/deploy/compose_env.sh"
resolve_compose_env "$2" "$1"
cd "$DOCKER_DIR"
exec $COMPOSE_CMD config --format json
'''
    argv = ["bash", "--noprofile", "--norc", "-c", script,
            "preflight-compose-config", os.path.abspath(repo_root), environment]
    if via_ssh:
        argv = ["ssh", "-o", "ClearAllForwardings=yes", "-o", "BatchMode=yes", via_ssh,
                " ".join(shlex.quote(part) for part in argv)]
    child_env = dict(os.environ)
    child_env.pop("BASH_ENV", None)
    try:
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, env=child_env)
    except (OSError, subprocess.TimeoutExpired):
        raise TargetUnreachable("cannot resolve the sanctioned Compose configuration; no target was probed")
    if completed.returncode:
        raise TargetUnreachable("sanctioned Compose configuration failed (exit {0}); inspect it privately on the Docker host".format(completed.returncode))
    try:
        document = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise TargetUnreachable("sanctioned Compose configuration returned invalid JSON; output withheld because it can contain secrets")
    return parse_context(document)


def choose_target(context, explicit_target=None, explicit_volume=None):
    """Preserve a named target; automatic checks describe the Compose runtime."""
    if explicit_volume is not None and not explicit_volume:
        _refuse("an explicit apps volume cannot be empty")
    if context.mode == "image-only":
        if explicit_volume is not None:
            _refuse("image-only mode forbids a Python clone overlay")
        return explicit_target or "image:" + context.image, None
    if explicit_volume is not None and explicit_volume != context.apps_volume:
        _refuse("explicit apps volume differs from the resolved deployment")
    # Existing explicit targets never acquired an implicit overlay. A caller
    # wanting the actual editable deployment must name its declared volume.
    if explicit_target:
        return explicit_target, explicit_volume
    return "image:" + context.image, context.apps_volume
