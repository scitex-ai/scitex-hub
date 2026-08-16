"""dispatch() must enforce its own allowlist, not trust the caller.

CodeQL py/partial-ssrf #10877 (critical) fires on _dispatch.py:52, where
``agent`` is interpolated into a URL path:

    url = f"{HUB_URL.rstrip('/')}/api/a2a/dispatch/{WORKSPACE}/{agent}/"

The 2026-08-05 triage called this "low-risk path-only", and read narrowly that
was right: the sole caller (a2a_app/views.py) gates on ``is_dispatchable`` and
the allowlist is exact set membership, so nothing traversable reaches the URL.

The problem is WHERE that guard lived. It was entirely in the caller, so the
sink's safety was a convention a second caller could silently break — the
"rule that must be remembered" the constitution says to replace with a
mechanical barrier. These tests pin the guard to the sink so it cannot be
bypassed by adding a caller.
"""

import pytest

from apps.infra.a2a_app import _dispatch


@pytest.fixture
def allowlist(monkeypatch):
    """Install a known allowlist for the duration of a test."""

    def _set(*agents):
        monkeypatch.setattr(_dispatch, "_DISPATCHABLE", set(agents))

    return _set


def test_agent_not_in_allowlist_is_refused(allowlist):
    allowlist("known-agent")
    with pytest.raises(ValueError) as exc:
        _dispatch.dispatch("unknown-agent", {})
    assert "not dispatchable" in str(exc.value)


def test_empty_allowlist_refuses_everything(allowlist):
    """The default when the env var is unset — must fail closed, not open."""
    allowlist()
    with pytest.raises(ValueError):
        _dispatch.dispatch("anyone", {})


@pytest.mark.parametrize(
    "agent",
    [
        "../admin",
        "..%2Fadmin",
        "known-agent/../../escape",
        "known-agent/extra",
        "/absolute",
    ],
)
def test_path_shaped_agents_are_refused(allowlist, agent):
    """Exact set membership means a traversal-shaped name is simply not a
    member. Asserted rather than assumed, because the whole reason this is a
    critical alert is that `agent` lands in a URL path."""
    allowlist("known-agent")
    with pytest.raises(ValueError):
        _dispatch.dispatch(agent, {})


def test_the_guard_runs_before_any_network_call(allowlist, monkeypatch):
    """A refusal must not reach urlopen — otherwise the request is already
    built and only the response is discarded."""
    allowlist("known-agent")
    called = []
    monkeypatch.setattr(
        _dispatch.urllib.request,
        "urlopen",
        lambda *a, **k: called.append(1),
    )
    with pytest.raises(ValueError):
        _dispatch.dispatch("not-allowed", {})
    assert called == [], "urlopen was reached despite a refused agent"


def test_allowlisted_agent_still_passes_the_guard(allowlist, monkeypatch):
    """Positive control. Without this, a guard that refused EVERYTHING would
    pass every test above while breaking dispatch entirely."""
    allowlist("known-agent")

    class _Resp:
        status = 200

        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        _dispatch.urllib.request, "urlopen", lambda *a, **k: _Resp()
    )
    status, payload = _dispatch.dispatch("known-agent", {"jsonrpc": "2.0"})
    assert status == 200
    assert payload == {"ok": True}
