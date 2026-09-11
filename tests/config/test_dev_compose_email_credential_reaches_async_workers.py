"""Every service that can send email must receive the SMTP credential.

OBSERVED FAILURE (#780, 2026-09-11): the live django container had
``SCITEX_HUB_EMAIL_HOST_PASSWORD`` while ``celery_worker`` did NOT. The worker's
startup check reported ``auth_app.E001``, and asynchronous OTP mail could fail
while the web signup form looked perfectly healthy — the worst shape for a
reliability bug, because the symptom appears on a page nobody is looking at.

CAUSE: ``docker-compose.yml`` injected the shell-only password into ``django`` and
nowhere else. The async services got the checked-in ``.env`` plus settings, so a
deliberately un-persisted credential was simply absent.

TWO THINGS MUST HOLD, and they pull in opposite directions:

  1. every email-sending service DECLARES the variable, or async mail breaks;
  2. the DECLARATION IS NEVER A VALUE — it is a shell substitution that fails
     loudly when the operator has not decrypted their credential first, so the
     secret stays out of the repository, out of rendered compose output and out of
     process arguments.

These tests assert both, and assert the second over the whole deployment tree
rather than just the file that changed.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
DEV_COMPOSE = REPO / "deployment/docker/docker_dev/docker-compose.yml"

CREDENTIAL = "SCITEX_HUB_EMAIL_HOST_PASSWORD"

#: Services that must be able to deliver mail. ``celery_beat`` is included
#: deliberately: even if beat only DISPATCHES, it runs Django startup checks, so a
#: beat without the credential can refuse to start over a capability it does not
#: itself use.
REQUIRED = {"django", "celery_worker", "celery_beat"}

#: Anything matching these is a declared-by-substitution form, not a stored secret.
def _is_substitution(value: str) -> bool:
    return value.startswith("${") and value.endswith("}")


@pytest.fixture(scope="module")
def dev_services() -> dict:
    return yaml.safe_load(DEV_COMPOSE.read_text(encoding="utf-8"))["services"]


def _environment(service: dict) -> list[str]:
    """The environment as a flat list of strings, whatever shape compose uses."""
    env = service.get("environment") or []
    if isinstance(env, dict):
        return [f"{k}={v}" for k, v in env.items()]
    return [str(entry) for entry in env]


def _credential_entry(service: dict) -> str | None:
    for entry in _environment(service):
        if entry.startswith(f"{CREDENTIAL}="):
            return entry
    return None


# ---------------------------------------------------------------------------
# 1. Coverage: every email-sending service declares it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_the_service_declares_the_credential(name, dev_services):
    """Absent here means that service cannot send OTP mail."""
    assert name in dev_services, f"{name} is not in the dev compose file"

    entry = _credential_entry(dev_services[name])
    assert entry is not None, (
        f"{name} does not declare {CREDENTIAL}, so it cannot deliver email. This is "
        "exactly the #780 failure: django had it, celery_worker did not, and async "
        "OTP mail failed while the web form looked healthy."
    )


def test_every_celery_service_declares_it_not_just_the_known_ones(dev_services):
    """CONTROL for future services: a new celery_* must not be missed.

    Naming the three known services would not survive someone adding
    ``celery_flower`` or a second queue worker, so the rule is applied to the whole
    celery family rather than to a hand-written list.
    """
    celery_services = sorted(n for n in dev_services if n.startswith("celery"))
    assert celery_services, "no celery services found — the compose layout changed"

    missing = [n for n in celery_services if _credential_entry(dev_services[n]) is None]
    assert not missing, (
        f"these celery services cannot send mail because {CREDENTIAL} is missing: "
        f"{missing}"
    )


# ---------------------------------------------------------------------------
# 2. Safety: the declaration is a substitution, never a stored value.
# ---------------------------------------------------------------------------


def test_the_declaration_is_a_shell_substitution_that_fails_when_unset(dev_services):
    """It must be shell-resolved AND fail loudly rather than defaulting to empty.

    ``${VAR:?message}`` aborts compose when the variable is unset; ``${VAR:-}``
    would start the container with an empty password and reproduce #780 silently.
    """
    for name in sorted(REQUIRED):
        entry = _credential_entry(dev_services[name])
        assert entry is not None, f"{name} declares nothing"
        value = entry.split("=", 1)[1]

        assert _is_substitution(value), (
            f"{name} embeds a literal value for {CREDENTIAL}. The credential is "
            f"shell-only by design; a literal here would be committed."
        )
        assert value.startswith(f"${{{CREDENTIAL}:?"), (
            f"{name} uses {value!r}, which does not fail when the credential is "
            "unset — the container would start with an empty password and async "
            "mail would fail exactly as in #780"
        )


def test_no_compose_file_anywhere_commits_a_credential_value():
    """Applied to the WHOLE deployment tree, not only the file that changed.

    A value introduced in staging or prod compose would be just as committed, and
    a test that only looked at docker_dev would not notice.
    """
    offenders: list[str] = []
    pattern = re.compile(rf"{CREDENTIAL}=(.+)$", re.MULTILINE)

    for path in sorted((REPO / "deployment/docker").rglob("*")):
        if path.is_dir() or path.suffix not in {".yml", ".yaml", ".example", ".env"}:
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = pattern.search(line.strip())
            if not match:
                continue
            value = match.group(1).strip()
            if _is_substitution(value):
                continue
            # A documented placeholder is not a secret; a real-looking value is.
            if value.upper().startswith(("CHANGE_ME", "YOUR_", "PLACEHOLDER", "EXAMPLE")):
                continue
            offenders.append(f"{path.relative_to(REPO)}: {CREDENTIAL}=<value>")

    assert not offenders, (
        "these files appear to commit a value for the SMTP credential: "
        f"{offenders}. The credential must be supplied by the shell from the "
        "encrypted ~/.pw source of truth."
    )


def test_the_control_can_see_a_literal_when_one_exists():
    """CONTROL — proves the scan above is not vacuous.

    A detector that never matches would pass the test above while committing a
    secret, so the same logic is pointed at a synthetic literal and must flag it.
    """
    pattern = re.compile(rf"{CREDENTIAL}=(.+)$", re.MULTILINE)
    sample = f"{CREDENTIAL}=hunter2-not-a-real-secret"  # pragma: allowlist secret

    match = pattern.search(sample)
    assert match is not None, "the detector does not match a plain assignment at all"
    assert not _is_substitution(match.group(1).strip()), (
        "a plain assignment was treated as a substitution, so the scan cannot fail"
    )
