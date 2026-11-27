# Mail routing policy

Decided by the operator on 2026-11-27, after his personal inbox was flooded
with Django error mail. Every outgoing message has a dedicated address per
purpose. This table is the policy for the whole SciTeX fleet; the Hub's
copy of the addresses lives in `config/branding.py` (`NOREPLY_EMAIL`,
`OPS_ALERT_EMAIL`, `CONTACT_EMAIL`).

| Purpose | From | To |
|---|---|---|
| System/ops alerts: Django ADMINS error mail, site-down alarm, storage alarms, CI/infra alerts | no-reply@scitex.ai | dev@scitex.ai |
| User-facing mail: signup/verification/password/notifications | no-reply@scitex.ai | the user |
| Agent → operator notices: decisions needed, agent stopped | agent@scitex.ai (display name "SciTeX Agent (<agent>)") | ywatanabe@scitex.ai |
| Inquiry alerts (contact form) | no-reply@scitex.ai | info@scitex.ai (plus the operator) |

## How the Hub implements it

| Mail | Setting | Env override | Default |
|---|---|---|---|
| Django error mail (`mail_admins`) recipients | `ADMINS`, `MANAGERS` | `SCITEX_HUB_ADMINS`, `SCITEX_HUB_MANAGERS` (comma-separated `addr` or `Name <addr>`) | `dev@scitex.ai`; MANAGERS follows ADMINS |
| Django error mail sender | `SERVER_EMAIL` | `SCITEX_HUB_SERVER_EMAIL` | `no-reply@scitex.ai` |
| User-facing mail sender | `DEFAULT_FROM_EMAIL` | `SCITEX_HUB_DEFAULT_FROM_EMAIL` | `no-reply@scitex.ai` |
| Site-down / recovery / flood alarm recipient | `public_app/tasks/health.py` | `SCITEX_HUB_HEALTH_NOTIFICATION_RECIPIENT` | `dev@scitex.ai` |
| Site-down alarm sender | same | `SCITEX_HUB_HEALTH_NOTIFICATION_SENDER` | `no-reply@scitex.ai` |
| Inquiry alerts | `INQUIRY_NOTIFY_TO`, `SERVICES_INQUIRY_EMAIL` | see PR #1241 | operator + info@ |

The senders are explicit settings. They used to be `EMAIL_HOST_USER`
implicitly, so the From depended on whichever SMTP login the env file held.
The SMTP account must be allowed to send as `no-reply@scitex.ai`; it is that
mailbox's own login in every deployment.

## Repeat suppression for error mail

`mail_admins` carries the `suppress_repeated_errors` filter
(`config/settings/_suppress_repeated_errors.py`):

- The same subject is mailed at most once per window. The window is one hour
  by default (`SCITEX_HUB_ADMIN_MAIL_REPEAT_WINDOW_SECONDS`).
- "Same subject" means the same logger, level, first message line and
  exception type. Digit runs and hex ids are folded, so a log line that embeds
  a changing row id or UUID is still one subject.
- The window lives in the Django `default` cache (Redis), so it holds across
  every gunicorn and celery worker. If the cache is unreachable, each process
  falls back to its own in-memory window. It never falls back to sending
  everything.
- The first mail of the next window states how many repeats were suppressed.
- A different error always gets through. Log files keep every record.
