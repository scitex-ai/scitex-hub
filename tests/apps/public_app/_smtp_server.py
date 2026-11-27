#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A tiny REAL SMTP server for tests: EHLO, STARTTLS, AUTH, MAIL/RCPT/DATA.

scitex-notification talks to SMTP with stdlib ``smtplib`` (it always issues
STARTTLS), so a Django locmem backend cannot observe it. This server speaks the
protocol over a real socket on 127.0.0.1 with a throwaway self-signed
certificate, records every accepted message, and can be told to refuse the
login the way prod's server did (535). Nothing in the code under test is
patched.
"""

from __future__ import annotations

import datetime as _dt
import ipaddress
import os
import socket
import socketserver
import ssl
import tempfile
import threading
from dataclasses import dataclass, field
from email import message_from_bytes
from pathlib import Path


def _self_signed_context() -> tuple[ssl.SSLContext, Path]:
    """Server context plus the certificate path a client must trust.

    The certificate names both ``localhost`` and ``127.0.0.1`` as subject
    alternative names: scitex-notification >= 0.3.0 verifies the STARTTLS
    certificate AND host name (``ssl.create_default_context()``), and the tests
    connect by IP. Trust is granted through ``SSL_CERT_FILE`` while the server
    runs (see ``TestSMTPServer``), so the client's verification stays real.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=1))
        .not_valid_after(now + _dt.timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    tmp = Path(tempfile.mkdtemp(prefix="test-smtp-"))
    (tmp / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (tmp / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(tmp / "cert.pem", tmp / "key.pem")
    return ctx, tmp / "cert.pem"


@dataclass
class Received:
    mail_from: str
    rcpt_to: list[str]
    data: bytes

    @property
    def message(self):
        return message_from_bytes(self.data)


@dataclass
class SMTPState:
    refuse_login: bool = False
    messages: list[Received] = field(default_factory=list)
    logins: list[str] = field(default_factory=list)


class _Handler(socketserver.StreamRequestHandler):
    def _send(self, line: str):
        self.wfile.write((line + "\r\n").encode())
        self.wfile.flush()

    def _ehlo(self):
        self._send("250-localhost")
        if not self.tls:
            self._send("250-STARTTLS")
        self._send("250 AUTH PLAIN LOGIN")

    def handle(self):  # noqa: C901 -- one protocol loop
        state: SMTPState = self.server.state
        self.tls = False
        self._send("220 localhost test SMTP")
        mail_from, rcpts = "", []
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            line = raw.decode(errors="replace").rstrip("\r\n")
            verb = line.split(" ", 1)[0].upper()
            if verb in ("EHLO", "HELO"):
                self._ehlo()
            elif verb == "STARTTLS":
                self._send("220 ready for TLS")
                tls_sock = self.server.tls_context.wrap_socket(
                    self.connection, server_side=True
                )
                self.connection = tls_sock
                self.rfile = tls_sock.makefile("rb")
                self.wfile = tls_sock.makefile("wb")
                self.tls = True
            elif verb == "AUTH":
                state.logins.append(line.split(" ", 2)[1].upper())
                if line.upper().startswith("AUTH LOGIN") and len(line.split()) == 2:
                    self._send("334 VXNlcm5hbWU6")
                    self.rfile.readline()
                    self._send("334 UGFzc3dvcmQ6")
                    self.rfile.readline()
                if state.refuse_login:
                    self._send("535 5.7.8 authentication failed")
                else:
                    self._send("235 2.7.0 authenticated")
            elif verb == "MAIL":
                mail_from, rcpts = line.split(":", 1)[1].strip(" <>"), []
                self._send("250 ok")
            elif verb == "RCPT":
                rcpts.append(line.split(":", 1)[1].strip(" <>"))
                self._send("250 ok")
            elif verb == "DATA":
                self._send("354 end with .")
                chunks = []
                while True:
                    chunk = self.rfile.readline()
                    if chunk in (b".\r\n", b".\n", b""):
                        break
                    chunks.append(chunk[1:] if chunk.startswith(b"..") else chunk)
                state.messages.append(Received(mail_from, rcpts, b"".join(chunks)))
                self._send("250 queued")
            elif verb == "RSET":
                mail_from, rcpts = "", []
                self._send("250 ok")
            elif verb == "QUIT":
                self._send("221 bye")
                return
            else:
                self._send("250 ok")


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class TestSMTPServer:
    """Context manager: ``with TestSMTPServer() as smtp: smtp.port, smtp.state``."""

    __test__ = False  # not a pytest test class

    def __init__(self, refuse_login: bool = False):
        self.state = SMTPState(refuse_login=refuse_login)

    def __enter__(self):
        self._server = _Server(("127.0.0.1", 0), _Handler)
        self._server.state = self.state
        self._server.tls_context, cert = _self_signed_context()
        # ssl.create_default_context() reads SSL_CERT_FILE when it loads the
        # default verify paths, so the client trusts exactly this server.
        self._saved_cert_file = os.environ.get("SSL_CERT_FILE")
        os.environ["SSL_CERT_FILE"] = str(cert)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        if self._saved_cert_file is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = self._saved_cert_file
        return False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
