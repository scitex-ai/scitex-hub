#!/usr/bin/env python3
"""One-shot SMTP delivery diagnostic. Sends a real mail to an operator address
and reports whether the provider accepted it. Run inside the container:

  docker exec scitex-hub-dev-django-1 python manage.py shell \
      -c "exec(open('/app/scripts/diag_email_send.py').read())"

Does NOT print credentials. Recipient is operator-controlled via env
SCITEX_DIAG_EMAIL_TO (default ywatanabe@scitex.ai).
"""
import os
import sys
import smtplib
from django.conf import settings
from django.core.mail import EmailMessage

to = os.environ.get("SCITEX_DIAG_EMAIL_TO", "ywatanabe@scitex.ai")
print("=== EMAIL DIAGNOSTIC ===")
print("backend    =", settings.EMAIL_BACKEND)
print("host:port  = {}:{}".format(settings.EMAIL_HOST, settings.EMAIL_PORT))
print("use_tls    =", settings.EMAIL_USE_TLS, " use_ssl =", settings.EMAIL_USE_SSL)
print("from       =", settings.DEFAULT_FROM_EMAIL)
print("to         =", to)
print("pass set   =", bool(settings.EMAIL_HOST_PASSWORD))

# 1) Raw socket + STARTTLS + auth — the lowest-level truth (no Django masking).
print("\n--- raw SMTP handshake ---")
try:
    s = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20)
    s.set_debuglevel(0)
    print("greeting   =", s.ehlo()[1].decode()[:80] if s.ehlo() else "n/a")
    try:
        s.starttls()
        print("starttls   = OK")
    except Exception as e:
        print("starttls   = FAIL", type(e).__name__, str(e)[:120])
    try:
        s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        print("auth       = OK")
    except smtplib.SMTPAuthenticationError as e:
        print("auth       = AUTH-FAIL", e.smtp_code, str(e.smtp_error)[:120])
        s.quit(); sys.exit(2)
    from email.message import EmailMessage as RawEmailMessage

    msg = RawEmailMessage()
    msg["Subject"] = "[diag] scitex email test"
    msg["From"] = settings.DEFAULT_FROM_EMAIL
    msg["To"] = to
    msg.set_content("If you receive this, SMTP delivery works. (automated diagnostic)")
    s.send_message(msg)
    print("smtp_send  = OK (provider accepted the message)")
    s.quit()
except Exception as e:
    print("raw smtp   = ERROR", type(e).__name__, str(e)[:200])
    sys.exit(1)

# 2) Django send_mail (fail_silently=False) — the exact path signup uses.
print("\n--- django send_mail (signup path) ---")
try:
    sent = EmailMessage(
        subject="[diag] scitex email test (django)",
        body="Django send_mail path. (automated diagnostic)",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    ).send()
    print("django_send= OK, accepted_by_provider_count =", sent)
except Exception as e:
    print("django_send= FAIL", type(e).__name__, str(e)[:200])
    sys.exit(3)
print("\n=== done: provider ACCEPTED both; if not delivered, it is a MAILBOX/DNS/reputation issue, not a send failure ===")
