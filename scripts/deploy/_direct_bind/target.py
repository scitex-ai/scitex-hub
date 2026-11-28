"""Build a real prospective editable environment without serving-state mounts."""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from preflight_targets import Target, TargetUnreachable

from . import snapshot
from .installation import private_exception_log, run_install


UV_CACHE_ENV = "SCITEX_HUB_PREFLIGHT_UV_CACHE"
UV_CACHE_TARGET = "/preflight-uv-cache"


def uv_cache_args(environ):
    """docker-create arguments that give the install a persistent uv cache.

    Without one, every preflight downloads the cohort's wheels again (torch
    and CUDA wheels are several GB), which is what pushed the install past its
    deadline. ``SCITEX_HUB_PREFLIGHT_UV_CACHE`` names an absolute host
    directory; unset means no cache, exactly as before. The cache holds only
    downloaded distributions, never an installed environment, so a stale entry
    cannot change what the check verifies.
    """
    path = (environ.get(UV_CACHE_ENV) or "").strip()
    if not path:
        return []
    if not os.path.isabs(path) or not os.path.isdir(path):
        raise TargetUnreachable(
            "{0} must name an existing absolute directory".format(UV_CACHE_ENV)
        )
    return [
        "--mount",
        "type=bind,src={0},dst={1}".format(path, UV_CACHE_TARGET),
        "--env",
        "SCITEX_PREFLIGHT_UV_CACHE_DIR=" + UV_CACHE_TARGET,
    ]


class DirectBindTarget(Target):
    def __init__(self, context, timeout, docker_timeout=60):
        self.token = uuid.uuid4().hex
        self.workspace = Path(tempfile.mkdtemp(prefix="scitex-hub-preflight-"))
        self.workspace.chmod(0o700)
        (self.workspace / "owner.json").write_text(
            json.dumps({"token": self.token, "uid": os.getuid(), "gid": os.getgid()})
        )
        self.volume = "scitex-hub-preflight-" + self.token
        self.install_name = self.volume + "-install"
        self.probe_name = self.volume + "-probe"
        self.sources = {}
        self.image = None
        self.created_volume = False
        self.pending_create = False
        self.stage = "inspect image"
        self.timeout = timeout
        # Deadline for each docker management call (inspect/create/run/rm/volume):
        # under host IO contention these take far longer than their idle cost.
        self.docker_timeout = docker_timeout
        super().__init__(
            "direct-bind", "prospective image and normal editable cohort", [], True
        )
        try:
            self._prepare(context)
        except Exception as preparation_error:
            try:
                self._close()
            except TargetUnreachable:
                raise
            except Exception as cleanup_error:
                path = private_exception_log(preparation_error, cleanup_error)
                raise TargetUnreachable(
                    "prospective preparation and owned cleanup failed; "
                    "private diagnostics: {0}; no deployment changed".format(path)
                ) from preparation_error
            if isinstance(preparation_error, subprocess.TimeoutExpired):
                raise TargetUnreachable(
                    "owned development preparation timed out during {0}; "
                    "no deployment changed".format(self.stage)
                ) from None
            raise

    def _prepare(self, context):
        self.image = json.loads(
            subprocess.check_output(
                ["docker", "image", "inspect", context.image],
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )
        )[0]["Id"]
        self.stage = "snapshot sources"
        directory = self.workspace / "sources"
        directory.mkdir()
        self.sources, objects = snapshot.prepare(context.direct_sources, directory)
        command = [
            "docker",
            "volume",
            "create",
            "--label",
            "scitex.hub.preflight=" + self.token,
            self.volume,
        ]
        self.stage = "create owned volume"
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.docker_timeout,
        )
        self.created_volume = True
        mounts = []
        for target, row in self.sources.items():
            mounts += [
                "--mount",
                "type=bind,src={0},dst={1}".format(row["snapshot"], target),
            ]
        for path in objects:
            mounts += ["--mount", "type=bind,src={0},dst={0},readonly".format(path)]
        mounts += ["--mount", "type=volume,src={0},dst=/preflight".format(self.volume)]
        mounts += uv_cache_args(os.environ)
        driver = Path(__file__).with_name("profile.py").resolve()
        create = [
            "docker",
            "create",
            "--name",
            self.install_name,
            "--label",
            "scitex.hub.preflight=" + self.token,
            "--network",
            "bridge",
            "--no-healthcheck",
            "--cpus",
            "2",
            "--memory",
            "8g",
            "--memory-swap",
            "8g",
            *mounts,
            "--mount",
            "type=bind,src={0},dst=/preflight-profile.py,readonly".format(driver),
            "--entrypoint",
            "python3",
            self.image,
            "-I",
            "-S",
            "-B",
            "-c",
            "import time; time.sleep(1200)",
        ]
        self.stage = "create owned preparation container"
        self.pending_create = True
        subprocess.run(
            create,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.docker_timeout,
        )
        self.pending_create = False
        self.stage = "start owned preparation container"
        subprocess.run(
            ["docker", "start", self.install_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.docker_timeout,
        )
        install = [
            "docker",
            "exec",
            "-i",
            self.install_name,
            "python3",
            "/preflight-profile.py",
        ]
        spec = {"sources": self.sources, "uid": os.getuid(), "gid": os.getgid()}
        self.stage = "normal editable install and source verification"
        run_install(install, spec, self.timeout)
        snapshot.verify(self.sources)
        # Probe the exact installed image-plus-editables graph, without a
        # second resolver or a fabricated metadata overlay. Disconnect ONLY
        # this owned container; no serving network or source is modified.
        self.stage = "disconnect owned network"
        subprocess.run(
            ["docker", "network", "disconnect", "bridge", self.install_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.docker_timeout,
        )
        self.stage = "verify owned network"
        document = json.loads(
            subprocess.check_output(
                ["docker", "inspect", self.install_name],
                stderr=subprocess.PIPE,
                timeout=self.docker_timeout,
            )
        )[0]
        if document["NetworkSettings"]["Networks"]:
            raise TargetUnreachable("owned prospective probe still has a network")
        self.argv = [
            "docker",
            "exec",
            "-i",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            self.install_name,
            "python3",
            "-",
        ]

    def verify_current(self):
        try:
            snapshot.verify(self.sources)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            raise TargetUnreachable(
                "development source changed or became unreadable during preflight"
            ) from exc

    def close(self):
        try:
            self._close()
        except TargetUnreachable:
            raise
        except Exception as exc:
            path = private_exception_log(exc)
            raise TargetUnreachable(
                "owned development preflight cleanup failed; private diagnostics: "
                "{0}; no deployment was changed".format(path)
            ) from exc

    def _close(self):
        for name in (self.install_name, self.probe_name):
            value = subprocess.run(
                ["docker", "inspect", name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.docker_timeout,
            )
            if value.returncode and name == self.install_name and self.pending_create:
                from .pending_creation import preserve_pending_creation

                raise TargetUnreachable(preserve_pending_creation(self))
            if value.returncode == 0:
                document = json.loads(value.stdout)[0]
                if (
                    document["Config"]["Labels"].get("scitex.hub.preflight")
                    != self.token
                ):
                    raise TargetUnreachable(
                        "owned preflight container identity changed"
                    )
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.docker_timeout,
                )
        if self.created_volume:
            volume = json.loads(
                subprocess.check_output(
                    ["docker", "volume", "inspect", self.volume],
                    stderr=subprocess.PIPE,
                    timeout=self.docker_timeout,
                )
            )[0]
            if volume.get("Labels", {}).get("scitex.hub.preflight") != self.token:
                raise TargetUnreachable("owned preflight volume identity changed")
            subprocess.run(
                ["docker", "volume", "rm", self.volume],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.docker_timeout,
            )
            self.created_volume = False
        if self.image is not None:
            # A killed build cannot run its finally block. Recover ownership of
            # ONLY this fresh, marked workspace; no original sources are mounted.
            code = """import json,os,sys
root='/owned-preflight-cleanup'
owner=json.load(open(root+'/owner.json'))
assert owner['token']==sys.argv[1]
for directory,names,files in os.walk(root,followlinks=False):
 for name in names+files:os.lchown(os.path.join(directory,name),owner['uid'],owner['gid'])
 os.lchown(directory,owner['uid'],owner['gid'])
"""
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--label",
                    "scitex.hub.preflight=" + self.token,
                    "--mount",
                    "type=bind,src={0},dst=/owned-preflight-cleanup".format(
                        self.workspace
                    ),
                    "--entrypoint",
                    "python3",
                    self.image,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    code,
                    self.token,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.docker_timeout,
            )
        shutil.rmtree(self.workspace)


def prepare(context, timeout, docker_timeout=60):
    try:
        return DirectBindTarget(context, timeout, docker_timeout)
    except TargetUnreachable:
        raise
    except Exception as exc:
        path = private_exception_log(exc)
        raise TargetUnreachable(
            "prospective direct-bind profile could not be prepared ({0}); "
            "private diagnostics: {1}; no deployment changed".format(
                type(exc).__name__, path
            )
        ) from exc
