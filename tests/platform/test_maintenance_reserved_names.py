"""New probe routes must not be offered as account profile names."""

import sys
from types import ModuleType

import pytest
from django.test import override_settings

from apps.infra.auth_app.validators import validate_username


@pytest.mark.parametrize("fallback", [False, True])
def test_probe_names_are_reserved_and_other_names_remain_valid(monkeypatch, tmp_path, fallback):
    with override_settings(BASE_DIR=tmp_path):
        from config.urls_helpers import get_reserved_paths

        paths = get_reserved_paths()
    assert {"livez", "maintenance-ready"} <= set(paths)
    if fallback:
        # Simulate URLconf import unavailability without loading deployed apps.
        monkeypatch.setitem(sys.modules, "config.urls", None)
    else:
        urls = ModuleType("config.urls")
        urls.RESERVED_PATHS = paths
        monkeypatch.setitem(sys.modules, "config.urls", urls)
    for username in ("livez", "Livez", "maintenance-ready", "livez-team"):
        valid, reason = validate_username(username)
        assert not valid
        assert "reserved" in reason
    assert validate_username("researcher-01") == (True, None)
