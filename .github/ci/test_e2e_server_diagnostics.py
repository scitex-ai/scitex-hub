"""Actual owned-process, filesystem and HTTP controls for diagnostic-only code."""

import importlib.util
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODULE = (
    Path(__file__).resolve().parents[2] / "tests/e2e/playwright/server_diagnostics.py"
)
spec = importlib.util.spec_from_file_location("owned_e2e_diagnostics", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OwnedDiagnosticControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="e2e-observer-", dir="/tmp")
        self.root = Path(self.temporary.name)
        self.log = (self.root / "server.log").open("w")
        self.process = None

    def tearDown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=12)
        self.log.close()
        self.temporary.cleanup()

    def start(self, body):
        (self.root / "manage.py").write_text(body)
        self.state = self.root / "state"
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(MODULE),
                "serve",
                "--root",
                str(self.root),
                "--state",
                str(self.state),
            ],
            stdout=self.log,
            stderr=self.log,
        )
        deadline = time.monotonic() + 5
        while not (self.state / "identity.json").exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                self.fail("Owned supervisor did not attest its child")
            time.sleep(0.01)
        return module.private_json(self.state / "identity.json")

    def test_real_exit_is_recorded_without_requested_termination(self):
        self.start("import time\ntime.sleep(.15)\nraise SystemExit(7)\n")
        self.assertEqual(self.process.wait(timeout=5), 7)
        observed = module.private_json(self.state / "exit.json")
        self.assertEqual(observed["exit_code"], 7)
        self.assertFalse(observed["termination_requested"])

    def test_real_child_signal_and_owned_stop(self):
        observed = self.start(
            "import time\nfrom pathlib import Path\nPath('ready').touch()\n"
            "while True: time.sleep(.1)\n"
        )
        deadline = time.monotonic() + 3
        while not (self.root / "ready").exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        self.assertTrue(module.matches(observed["child"]))
        os.kill(observed["child"]["pid"], signal.SIGUSR1)
        module.stop(self.state)
        self.process.wait(timeout=5)
        final = module.private_json(self.state / "exit.json")
        self.assertTrue(final["termination_requested"])
        self.assertFalse(module.matches(observed["child"]))
        self.assertIn("Current thread", (self.root / "server.log").read_text())
        self.assertTrue((self.state / "samples.jsonl").stat().st_size)

    def test_wrong_birth_or_command_refuses_stop_and_preserves_real_child(self):
        observed = self.start("import time\nwhile True: time.sleep(.1)\n")
        for field in ("birth", "command_sha256"):
            altered = json.loads(json.dumps(observed))
            altered["supervisor"][field] = "0"
            module.write_json(self.state / "identity.json", altered)
            with self.assertRaises(ValueError):
                module.stop(self.state)
            self.assertTrue(module.matches(observed["child"]))
        module.write_json(self.state / "identity.json", observed)
        module.stop(self.state)

    def test_post_spawn_metadata_write_failure_reaps_only_own_child(self):
        # A real kernel file-size refusal occurs after Popen, before identity
        # publication; the finally path must not leave the child running.
        (self.root / "manage.py").write_text("import time\ntime.sleep(20)\n")
        children = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")
        before = children.read_text()
        limits = resource.getrlimit(resource.RLIMIT_FSIZE)
        handler = signal.getsignal(signal.SIGXFSZ)
        try:
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, limits[1]))
            with self.assertRaises(OSError):
                module.serve(self.root / "refused-state", self.root)
        finally:
            resource.setrlimit(resource.RLIMIT_FSIZE, limits)
            signal.signal(signal.SIGXFSZ, handler)
        self.assertEqual(children.read_text(), before)

    def test_fifo_symlink_oversize_metadata_are_refused(self):
        fifo = self.root / "fifo"
        os.mkfifo(fifo, 0o600)
        with self.assertRaises(ValueError):
            module.private_json(fifo)
        large = self.root / "large"
        large.write_bytes(b" " * 65537)
        large.chmod(0o600)
        with self.assertRaises(ValueError):
            module.private_json(large)
        link = self.root / "link"
        link.symlink_to(large)
        with self.assertRaises(OSError):
            module.private_json(link)

    def test_redirect_never_forwards_cookie_or_reads_reply_body(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                received.append((self.path, self.headers.get("Cookie")))
                self.send_response(302 if self.path == "/redirect" else 200)
                self.send_header("Location", "/unapproved-target")
                self.end_headers()
                self.wfile.write(b"PRIVATE_REPLY_MUST_NOT_BE_SAVED")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            observed = module.http_probe(
                f"http://127.0.0.1:{server.server_port}/redirect", "owned=COOKIE_CANARY"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(observed["status"], 302)
        self.assertEqual(received, [("/redirect", "owned=COOKIE_CANARY")])
        self.assertNotIn("COOKIE_CANARY", json.dumps(observed))
        self.assertNotIn("PRIVATE_REPLY", json.dumps(observed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
