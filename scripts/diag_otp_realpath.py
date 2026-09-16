#!/usr/bin/env python3
"""Decisive test of the REAL signup OTP send path (EmailService.send_otp_email),
not a plain EmailMessage. Captures the true return value + any exception so we
know whether signup's 'email sent' is a real provider-accept or a masked failure.
Recipient is operator-controlled (SCITEX_DIAG_EMAIL_TO, default the operator).
Does NOT print credentials.
"""
import os
import logging
logging.disable(logging.CRITICAL)
from django.conf import settings
from apps.infra.project_app.services.email_service import EmailService

to = os.environ.get("SCITEX_DIAG_EMAIL_TO", "ywatanabe@scitex.ai")
print("=== REAL signup OTP path: EmailService.send_otp_email ===")
print("backend =", settings.EMAIL_BACKEND)
print("from    =", settings.DEFAULT_FROM_EMAIL)
print("to      =", to)
try:
    success, message = EmailService.send_otp_email(email=to, otp_code="000000", verification_type="signup")
    print("RETURN  =", (success, message))
    print("VERDICT =", "provider ACCEPTED the OTP email via the exact signup code path" if success else "send_otp_email returned FAILURE -> signup would show the warning, not 'email sent'")
except Exception as e:
    import traceback
    print("RAISED  =", type(e).__name__, str(e)[:400])
    traceback.print_exc()
    print("VERDICT = exception in send path -> would be caught by view's except and shown as a warning")
