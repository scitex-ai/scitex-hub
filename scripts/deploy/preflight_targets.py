#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Choosing, reaching, and interrogating THE THING THAT WILL RUN.

Picking the wrong target reproduces the 2026-08-18 mistake in a new costume, so
the choices are spelled out rather than defaulted:

``image:<ref>``      The artifact the next recreate will run. This is the deploy
                     gate's target. Measured 2026-08-22: scitex-hub-prod-django:latest
                     has no scitex-sh and no scitex-decorators, and raises
                     ImportError on ``import scitex.io`` -- the outage is in the
                     image, one ``up -d`` away.

``container:<name>`` What is serving RIGHT NOW. Useful, and WRONG as the deploy
                     gate. On 2026-08-22 the running container reported
                     scitex-sh 0.2.0 present, because someone had pip-installed
                     it into the writable layer that morning; ``docker diff``
                     showed both packages as 'A' (added), so the recreate
                     deletes them. A gate asking this container would have been
                     green while the recreate took prod down.

``local``            The shell the preflight itself runs in. This is NOT a target
                     check and the driver says so in capitals every time it is
                     used. It exists for developing the preflight, not for
                     gating a deploy.

``cmd:<argv>``       Any command that reads Python on stdin and runs it inside
                     the environment under test. This is what makes the gate
                     testable against a constructed environment, and what makes
                     it reachable over ssh without teaching it about ssh.

THE BOOT OVERLAY, and why the image alone is not the whole answer.
``entrypoint-prod.sh`` runs ``scripts/apps/install_apps.sh`` at EVERY container
start, editable-installing the apps in ``.scitex-apps.json`` from git clones on a
persistent volume. Those installs override the image's wheels: measured, the
image ships scitex-writer 2.26.1 and the running container serves 2.42.0 from
``/app/.apps/scitex-writer``. So when the caller names that volume, it is mounted
READ-ONLY into the throwaway container and each clone's ``src`` is prepended to
``sys.path`` -- which is what the editable install does -- and the clone's
declared version is read as the overlay answer.

Everything here is read-only against the deployment: ``--rm`` throwaway
containers, ``--network none``, ``--entrypoint python`` so the image's entrypoint
(root-init, migrations, install_apps) never runs, and ``:ro`` on the mount.
"""

import json
import os
import shlex
import subprocess
import sys

from preflight_probe import REPORT_BEGIN, REPORT_END

#: Where the boot overlay clones live inside the container.
APPS_MOUNTPOINT = "/app/.apps"


class TargetUnreachable(Exception):
    """The target could not be interrogated. Never downgraded to 'probably fine'."""


class Target(object):
    """A resolved way to execute Python inside the deployment under test."""

    def __init__(self, kind, description, argv, is_target_check, overlay=None, extra_syspath=()):
        self.kind = kind
        self.description = description
        self.argv = list(argv)
        #: False only for ``local``. The driver refuses to call itself a target
        #: check when this is False, however green the result looks.
        self.is_target_check = is_target_check
        self.overlay = dict(overlay or {})
        self.extra_syspath = list(extra_syspath)

    @property
    def command(self):
        return " ".join(shlex.quote(part) for part in self.argv)


def _docker_available():
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if directory and os.path.isfile(os.path.join(directory, "docker")):
            return True
    return False


def _apps_from_manifest(manifest_path):
    """``{distribution: clone_dir}`` for the apps the boot overlay reinstalls.

    The manifest's ``pip_package`` is the distribution the editable install
    publishes, and ``name`` is the directory the clone lands in -- these differ
    (``scitex-todo`` clones ``scitex-cards.git``), which is exactly why this is
    read from the manifest instead of guessed.
    """
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    out = {}
    for app in manifest.get("apps", []):
        name = app.get("name")
        package = app.get("pip_package") or name
        if name:
            out[package] = "{0}/{1}".format(APPS_MOUNTPOINT, name)
    if not out:
        raise TargetUnreachable(
            "{0} lists no apps; the boot overlay would be silently ignored".format(manifest_path)
        )
    return out


def resolve(spec, apps_volume=None, apps_manifest=None, via_ssh=None):
    """Build a :class:`Target` from a ``--target`` string."""
    overlay = {}
    extra_syspath = []
    mounts = []

    if apps_volume:
        if not apps_manifest or not os.path.isfile(apps_manifest):
            raise TargetUnreachable(
                "--apps-volume was given but the manifest {0!r} is missing; the boot "
                "overlay cannot be described without it".format(apps_manifest)
            )
        overlay = _apps_from_manifest(apps_manifest)
        # An editable install of a src-layout project puts <clone>/src on
        # sys.path. Measured on prod 2026-08-22: all five clones resolve as
        # /app/.apps/<name>/src/<module>/__init__.py.
        extra_syspath = ["{0}/src".format(clone) for clone in sorted(overlay.values())]
        mounts = ["-v", "{0}:{1}:ro".format(apps_volume, APPS_MOUNTPOINT)]

    if spec == "local":
        if apps_volume:
            raise TargetUnreachable("--apps-volume is meaningless for --target local")
        return Target(
            "local",
            "the shell the preflight itself is running in ({0})".format(sys.executable),
            [sys.executable, "-"],
            is_target_check=False,
        )

    if spec.startswith("cmd:"):
        argv = shlex.split(spec[len("cmd:"):])
        if not argv:
            raise TargetUnreachable("--target cmd: needs a command")
        return Target(
            "cmd",
            "custom runner: {0}".format(" ".join(shlex.quote(a) for a in argv)),
            argv,
            is_target_check=True,
            overlay=overlay,
            extra_syspath=extra_syspath,
        )

    if spec.startswith("image:"):
        ref = spec[len("image:"):]
        argv = ["docker", "run", "--rm", "-i", "--network", "none"] + mounts + [
            "--entrypoint", "python", ref, "-",
        ]
        description = "image {0}".format(ref)
        if apps_volume:
            description += " + boot overlay from volume {0}".format(apps_volume)
    elif spec.startswith("container:"):
        name = spec[len("container:"):]
        if apps_volume:
            raise TargetUnreachable(
                "--apps-volume is for image targets; a running container already has "
                "the overlay installed"
            )
        argv = ["docker", "exec", "-i", name, "python3", "-"]
        description = "running container {0} (what is serving now, NOT what the next recreate will run)".format(name)
    else:
        raise TargetUnreachable(
            "unrecognised --target {0!r}; want image:<ref>, container:<name>, local, or cmd:<argv>".format(spec)
        )

    if via_ssh:
        remote = " ".join(shlex.quote(part) for part in argv)
        argv = ["ssh", "-o", "ClearAllForwardings=yes", "-o", "BatchMode=yes", via_ssh, remote]
        description += " on {0} (over ssh)".format(via_ssh)

    if not via_ssh and not _docker_available():
        raise TargetUnreachable(
            "docker is not on PATH, so target {0!r} cannot be interrogated from this host. "
            "The deploy runs ON the docker host; if you are running this somewhere else, "
            "pass --via-ssh <host> or --target cmd:<argv>.".format(spec)
        )

    return Target(
        "image" if spec.startswith("image:") else "container",
        description,
        argv,
        is_target_check=True,
        overlay=overlay,
        extra_syspath=extra_syspath,
    )


def _tail(text, limit=2000):
    text = (text or "").strip()
    return text if len(text) <= limit else "...\n" + text[-limit:]


def interrogate(target, probe_source, spec, timeout=300):
    """Run the probe inside ``target`` and return its report.

    The spec is appended to the probe source as a literal call rather than passed
    as an argument, so no shell quoting sits between the driver and the target.
    """
    payload = probe_source + "\n\n_run(json.loads(" + repr(json.dumps(spec)) + "))\n"
    try:
        completed = subprocess.run(
            target.argv,
            input=payload.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise TargetUnreachable("cannot execute {0}: {1}".format(target.command, exc))
    except subprocess.TimeoutExpired:
        raise TargetUnreachable(
            "the target did not answer within {0}s: {1}".format(timeout, target.command)
        )

    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")

    if REPORT_BEGIN not in stdout or REPORT_END not in stdout:
        raise TargetUnreachable(
            "the target produced no preflight report (exit {0}).\n"
            "  command: {1}\n"
            "  stdout : {2}\n"
            "  stderr : {3}".format(completed.returncode, target.command, _tail(stdout), _tail(stderr))
        )

    body = stdout.split(REPORT_BEGIN, 1)[1].split(REPORT_END, 1)[0]
    try:
        report = json.loads(body)
    except ValueError as exc:
        raise TargetUnreachable("the target's report was not valid JSON: {0}".format(exc))
    report["_stderr_tail"] = _tail(stderr, 800)
    report["_exit_code"] = completed.returncode
    return report

# EOF
