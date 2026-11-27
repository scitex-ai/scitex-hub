#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Can this deployment actually deliver mail? A probe that does not send any.

WHY THIS EXISTS (scitex-hub#1234). From 2026-08 to 2026-11, no prod sign-up
finished email verification: 0 of 8. The cause was the configured SMTP account
being REFUSED at login (SMTP 535). The signup view, correctly, gives the same
generic reply whether or not the send worked (anything else is an
account-enumeration oracle). The resulting log line went to a file nobody read,
and the "operator notification rail" (mail_admins) uses the SAME broken SMTP
login. So the failure could not report itself, and the funnel showed only that
people stopped verifying.

The probe opens the configured backend exactly as a real send would: connect,
STARTTLS, and authenticate (Django's ``SMTPEmailBackend.open()`` does all
three). Then it closes. It sends nothing, so it is safe to run on every deploy
and from a schedule. It reports a STAGE and an SMTP status code, never the
server's free-text reply, because that reply can echo the account name.
"""

from __future__ import annotations

import smtplib
import socket
from dataclasses import dataclass

__all__ = ["MailProbe", "probe_mail_backend"]


@dataclass(frozen=True)
class MailProbe:
    """Outcome of one probe. ``detail`` is safe to print: no credentials."""

    ok: bool
    backend: str
    stage: str
    detail: str = ""

    def summary(self) -> str:
        state = "OK" if self.ok else "FAILED"
        tail = f" ({self.detail})" if self.detail else ""
        return f"mail backend {self.backend}: {state} at {self.stage}{tail}"


def probe_mail_backend(connection=None) -> MailProbe:
    """Open and close the configured mail connection, and report how far it got.

    Non-SMTP backends (console, file, locmem) open trivially and report ``ok``
    at stage ``open``. That is correct: they cannot fail to deliver to
    themselves, and dev/test deployments use them on purpose.
    """
    from django.conf import settings
    from django.core.mail import get_connection

    backend = getattr(settings, "EMAIL_BACKEND", "") or "<unset>"
    if connection is None:
        connection = get_connection(fail_silently=False)
    try:
        connection.open()
    except smtplib.SMTPAuthenticationError as exc:
        return MailProbe(False, backend, "login", f"SMTP {exc.smtp_code}")
    except smtplib.SMTPNotSupportedError:
        return MailProbe(False, backend, "starttls", "server does not offer STARTTLS")
    except smtplib.SMTPResponseException as exc:
        return MailProbe(False, backend, "handshake", f"SMTP {exc.smtp_code}")
    except (socket.timeout, TimeoutError):
        return MailProbe(False, backend, "connect", "timeout")
    except OSError as exc:
        # DNS failure, connection refused, TLS failure: name the class only.
        return MailProbe(False, backend, "connect", type(exc).__name__)
    finally:
        try:
            connection.close()
        except Exception:  # noqa: BLE001 -- closing a half-open socket may raise
            pass
    return MailProbe(True, backend, "open")


# EOF
