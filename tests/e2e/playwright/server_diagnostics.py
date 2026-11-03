"""Owned E2E server observations; no application responses or assertions change."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def private_json(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise ValueError("Unowned diagnostic metadata")
        if before.st_mode & 0o077 or before.st_size > 65536:
            raise ValueError("Diagnostic metadata permissions/size differ")
        raw = os.read(fd, 65537)
        after = os.fstat(fd)
        if len(raw) > 65536 or (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("Diagnostic metadata changed")
        return json.loads(raw)
    finally:
        os.close(fd)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    temporary.replace(path)


def identity(pid: int) -> dict:
    proc = Path("/proc") / str(pid)
    first = (proc / "stat").read_text().rsplit(") ", 1)[1].split()[19]
    if proc.stat().st_uid != os.getuid():
        raise ValueError("Diagnostic process owner differs")
    with (proc / "cmdline").open("rb") as stream:
        raw = stream.read(16385)
    if not raw or len(raw) > 16384:
        raise ValueError("Diagnostic command identity unavailable")
    second = (proc / "stat").read_text().rsplit(") ", 1)[1].split()[19]
    if first != second:
        raise ValueError("Diagnostic process generation changed")
    return {
        "pid": pid,
        "birth": first,
        "uid": os.getuid(),
        "command_sha256": hashlib.sha256(raw).hexdigest(),
    }


def matches(expected: dict) -> bool:
    try:
        return identity(expected["pid"]) == expected
    except (OSError, ValueError, KeyError):
        return False


def cgroup_directory(pid: int) -> Path | None:
    for line in (Path("/proc") / str(pid) / "cgroup").read_text().splitlines():
        if line.startswith("0::"):
            relative = Path(line[3:].lstrip("/"))
            if ".." in relative.parts:
                raise ValueError("Invalid diagnostic cgroup")
            root = Path("/sys/fs/cgroup").resolve()
            target = (root / relative).resolve()
            if target.is_relative_to(root):
                return target
    return None


def memory_sample(expected: dict, cgroup: Path | None) -> dict:
    result = {"monotonic": time.monotonic(), "identity_matches": matches(expected)}
    if result["identity_matches"]:
        status = (Path("/proc") / str(expected["pid"]) / "status").read_text()
        for line in status.splitlines():
            name, _, value = line.partition(":")
            if name in {"VmRSS", "VmHWM", "Threads"}:
                result[name] = value.strip()
    if cgroup:
        for name in ("memory.current", "memory.peak", "memory.max", "memory.events"):
            try:
                value = (cgroup / name).read_text()[:4096]
                if name == "memory.events":
                    allowed = {
                        "low",
                        "high",
                        "max",
                        "oom",
                        "oom_kill",
                        "oom_group_kill",
                    }
                    result[name] = {
                        k: int(v)
                        for k, v in (line.split() for line in value.splitlines())
                        if k in allowed
                    }
                else:
                    result[name] = value.strip()
            except (OSError, ValueError):
                result[name] = "unobservable"
    return result


def serve(directory: Path, root: Path) -> int:
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    boot = (
        "import faulthandler,signal,runpy,sys;"
        "faulthandler.enable();faulthandler.register(signal.SIGUSR1);"
        "sys.argv=['manage.py',*sys.argv[1:]];"
        "runpy.run_path('manage.py',run_name='__main__')"
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            boot,
            "runserver",
            "127.0.0.1:8000",
            "--noreload",
            "from_docker",
        ],
        cwd=root,
    )
    try:
        child_identity = identity(child.pid)
        record = {
            "schema": "owned-e2e-server/v1",
            "supervisor": identity(os.getpid()),
            "child": child_identity,
            "source": os.environ.get("GITHUB_SHA"),
            "started_monotonic": time.monotonic(),
            "termination_requested": False,
        }
        write_json(directory / "identity.json", record)
        cgroup = cgroup_directory(child.pid)
        requested_at = None

        def forward(signum, _frame):
            nonlocal requested_at
            if child.poll() is None and matches(child_identity):
                requested_at = requested_at or time.monotonic()
                record["termination_requested"] = True
                record["forwarded_signal"] = signum
                os.kill(child.pid, signum)

        signal.signal(signal.SIGTERM, forward)
        signal.signal(signal.SIGINT, forward)
        samples = directory / "samples.jsonl"
        fd = os.open(samples, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            while child.poll() is None:
                try:
                    sample = memory_sample(child_identity, cgroup)
                except (OSError, ValueError):
                    sample = {
                        "monotonic": time.monotonic(),
                        "process_unobservable": True,
                    }
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                if requested_at and time.monotonic() - requested_at >= 8:
                    if matches(child_identity):
                        record["escalated_owned_kill"] = True
                        os.kill(child.pid, signal.SIGKILL)
                time.sleep(1)
        record["exit_code"] = child.wait()
        record["finished_monotonic"] = time.monotonic()
        record["last_sample"] = memory_sample(child_identity, cgroup)
        write_json(directory / "exit.json", record)
        return (
            record["exit_code"]
            if record["exit_code"] >= 0
            else 128 - record["exit_code"]
        )
    finally:
        # Popen owns this unreaped child even if initial metadata capture fails.
        # A running, unreaped child PID cannot have been reused by another process.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)


def stop(directory: Path) -> None:
    record = private_json(directory / "identity.json")
    if not (directory / "exit.json").exists():
        if not matches(record["supervisor"]):
            raise ValueError("Diagnostic supervisor generation differs")
        os.kill(record["supervisor"]["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 12
    while not (directory / "exit.json").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if not (directory / "exit.json").exists():
        raise ValueError("Diagnostic supervisor did not record actual child exit")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_probe(url: str, cookies: str = "") -> dict:
    started = time.monotonic()
    headers = {"Cookie": cookies} if cookies else {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(
            urllib.request.Request(url, headers=headers), timeout=2
        ) as response:
            return {"status": response.status, "elapsed": time.monotonic() - started}
    except urllib.error.HTTPError as error:
        return {"status": error.code, "elapsed": time.monotonic() - started}
    except Exception as error:
        return {
            "error_type": type(error).__name__,
            "elapsed": time.monotonic() - started,
        }


def pg_probe() -> dict:
    import psycopg

    host = os.environ.get("SCITEX_HUB_DB_HOST_DEV")
    database = os.environ.get("SCITEX_HUB_DB_NAME_DEV")
    user = os.environ.get("SCITEX_HUB_DB_USER_DEV")
    if (
        host not in {"localhost", "127.0.0.1", "::1"}
        or database != "scitex_test"
        or user != "scitex"
    ):
        return {"refused": "not the declared owned CI PostgreSQL fixture"}
    try:
        with psycopg.connect(
            host=host,
            port=os.environ["SCITEX_HUB_DB_PORT_DEV"],
            dbname=database,
            user=user,
            password=os.environ["SCITEX_HUB_DB_PASSWORD_DEV"],
            connect_timeout=2,
            options="-c statement_timeout=1500",
        ) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            rows = connection.execute(
                "SELECT state,wait_event_type,wait_event,cardinality(pg_blocking_pids(pid)) "
                "FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() ORDER BY pid LIMIT 128"
            ).fetchall()
            return {"rows": rows}
    except Exception as error:
        return {"error_type": type(error).__name__}


_BROWSER_FACTS = {"service_workers": [], "requests": [], "responses": [], "ready": []}
_WATCHED_CONTEXTS = set()


def observe_browser(page) -> None:
    if not os.environ.get("SCITEX_E2E_DIAGNOSTIC_STATE"):
        return
    context = page.context
    if id(context) not in _WATCHED_CONTEXTS:
        _WATCHED_CONTEXTS.add(id(context))
        context.on(
            "serviceworker",
            lambda worker: _BROWSER_FACTS["service_workers"].append(
                urllib.parse.urlsplit(worker.url).path
            ),
        )

    def response_seen(response):
        _BROWSER_FACTS["responses"].append(
            {
                "path": urllib.parse.urlsplit(response.url).path,
                "from_service_worker": response.from_service_worker,
                "status": response.status,
            }
        )
        del _BROWSER_FACTS["responses"][:-256]

    def request_seen(request):
        _BROWSER_FACTS["requests"].append(
            {
                "path": urllib.parse.urlsplit(request.url).path,
                "resource_type": request.resource_type,
                "from_service_worker": request.service_worker is not None,
                "monotonic": time.monotonic(),
            }
        )
        del _BROWSER_FACTS["requests"][:-128]

    page.on("request", request_seen)
    page.on("response", response_seen)


def observe_ready(page) -> None:
    if not os.environ.get("SCITEX_E2E_DIAGNOSTIC_STATE"):
        return
    try:
        value = page.evaluate("""async () => {
          if (!('serviceWorker' in navigator)) return {supported:false};
          const controller=navigator.serviceWorker.controller;
          const read=navigator.serviceWorker.getRegistrations().then(rs=>({
            supported:true,controller:controller?.scriptURL || null,
            registrations:rs.map(r=>({scope:r.scope,state:r.active?.state || null}))}));
          return await Promise.race([read,new Promise(resolve=>setTimeout(
            ()=>resolve({observation_timeout:true}),500))]);
        }""")
        _BROWSER_FACTS["ready"].append(value)
    except Exception as error:
        _BROWSER_FACTS["ready"].append({"error_type": type(error).__name__})


def capture_timeout(page, href: str) -> None:
    """Observe the original failure before its page closes; never read bodies."""
    directory_value = os.environ.get("SCITEX_E2E_DIAGNOSTIC_STATE")
    if not directory_value:
        return
    directory = Path(directory_value)
    result = {"monotonic": time.monotonic(), "browser": _BROWSER_FACTS}
    try:
        href = urllib.parse.urljoin(os.environ["SCITEX_BASE_URL"], href)
        parsed = urllib.parse.urlsplit(href)
        base = urllib.parse.urlsplit(os.environ["SCITEX_BASE_URL"])
        if (parsed.scheme, parsed.netloc) != (
            base.scheme,
            base.netloc,
        ) or base.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Only the owned loopback app is observable")
        record = private_json(directory / "identity.json")
        if matches(record["child"]):
            os.kill(record["child"]["pid"], signal.SIGUSR1)
            result["event_stack_requested"] = True
        else:
            result["event_stack_requested"] = False
        origin = urllib.parse.urlunsplit((base.scheme, base.netloc, "", "", ""))
        result["health"] = http_probe(origin + "/healthz/")
        # Cookies remain in memory; neither cookies nor reply bodies are saved.
        cookies = "; ".join(
            item["name"] + "=" + item["value"] for item in page.context.cookies(href)
        )
        result["authenticated_app"] = http_probe(href, cookies)
        result["pg"] = pg_probe()
        result["failed_path"] = parsed.path
        if (directory / "exit.json").exists():
            result["server_exit"] = private_json(directory / "exit.json")
    except Exception as error:
        result["observation_error_type"] = type(error).__name__
    write_json(
        directory / ("navigation-timeout-" + str(time.monotonic_ns()) + ".json"), result
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "stop"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    if arguments.mode == "serve":
        raise SystemExit(serve(arguments.state, arguments.root))
    stop(arguments.state)
