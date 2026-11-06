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


class DirectBindTarget(Target):
    def __init__(self, context, timeout):
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
        self.timeout = timeout
        super().__init__(
            "direct-bind", "prospective image and normal editable cohort", [], True
        )
        try:
            self._prepare(context)
        except Exception:
            self.close()
            raise

    def _prepare(self, context):
        self.image = json.loads(
            subprocess.check_output(
                ["docker", "image", "inspect", context.image],
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )
        )[0]["Id"]
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
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
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
        driver = Path(__file__).with_name("profile.py").resolve()
        install = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--name",
            self.install_name,
            "--label",
            "scitex.hub.preflight=" + self.token,
            "--cpus",
            "2",
            "--memory",
            "8g",
            "--memory-swap",
            "8g",
            *mounts,
            "--mount",
            "type=bind,src={0},dst=/preflight-sources".format(directory),
            "--mount",
            "type=bind,src={0},dst=/preflight-profile.py,readonly".format(driver),
            "--entrypoint",
            "python3",
            self.image,
            "/preflight-profile.py",
        ]
        spec = {"sources": self.sources, "uid": os.getuid(), "gid": os.getgid()}
        completed = subprocess.run(
            install,
            input=json.dumps(spec).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
        )
        if completed.returncode:
            descriptor, log_path = tempfile.mkstemp(
                prefix="scitex-hub-preflight-", suffix=".private.log"
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(completed.stdout)
                stream.write(completed.stderr)
            raise TargetUnreachable(
                "normal prospective editable installation or dependency check failed; "
                "private diagnostics: {0}; no deployment was changed".format(log_path)
            )
        snapshot.verify(self.sources)
        readonly = []
        for target, row in self.sources.items():
            readonly += [
                "--mount",
                "type=bind,src={0},dst={1},readonly".format(row["snapshot"], target),
            ]
        readonly += [
            "--mount",
            "type=volume,src={0},dst=/preflight,readonly".format(self.volume),
        ]
        self.argv = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--name",
            self.probe_name,
            "--label",
            "scitex.hub.preflight=" + self.token,
            "--cpus",
            "2",
            "--memory",
            "8g",
            "--memory-swap",
            "8g",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            *readonly,
            "--entrypoint",
            "/preflight/env/bin/python",
            self.image,
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
            raise TargetUnreachable(
                "owned development preflight cleanup failed; no deployment was changed"
            ) from exc

    def _close(self):
        for name in (self.install_name, self.probe_name):
            value = subprocess.run(
                ["docker", "inspect", name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
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
                    timeout=60,
                )
        if self.created_volume:
            volume = json.loads(
                subprocess.check_output(
                    ["docker", "volume", "inspect", self.volume],
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
            )[0]
            if volume.get("Labels", {}).get("scitex.hub.preflight") != self.token:
                raise TargetUnreachable("owned preflight volume identity changed")
            subprocess.run(
                ["docker", "volume", "rm", self.volume],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
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
                timeout=60,
            )
        shutil.rmtree(self.workspace)


def prepare(context, timeout):
    try:
        return DirectBindTarget(context, timeout)
    except TargetUnreachable:
        raise
    except Exception as exc:
        raise TargetUnreachable(
            "prospective direct-bind profile could not be prepared ({0}); no deployment changed".format(
                type(exc).__name__
            )
        ) from exc
