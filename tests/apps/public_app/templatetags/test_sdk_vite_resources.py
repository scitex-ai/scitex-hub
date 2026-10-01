"""Real SDK source entries must use host Vite and its packaged assets."""
from pathlib import Path

from django.test import override_settings

from apps.infra.public_app.templatetags import vite


ENTRY = "scitex_sdk/ui/shell/resizer/index"


def test_canonical_sdk_entry_is_a_platform_entry():
    assert not vite._is_dev_app_entry(ENTRY)


def test_sdk_entry_resolves_the_actual_packaged_source():
    from scitex_sdk import ui

    source = Path(vite._entry_to_ts_path(ENTRY))
    assert source == (ui.get_static_dir() / "ts/shell/resizer/index.ts").resolve()
    assert source.is_file()


def test_sdk_dev_script_uses_the_vite_filesystem_route():
    with override_settings(DEBUG=True, VITE_USE_BUILD=False, VITE_HOST_PORT=5173):
        source = vite._entry_to_ts_path(ENTRY)
        script = str(vite.vite_script(ENTRY))
    assert f":5173/@fs{source}" in script
    assert "5174" not in script


def test_sdk_dev_asset_url_uses_the_same_filesystem_route():
    with override_settings(DEBUG=True, VITE_USE_BUILD=False, VITE_HOST_PORT=5173):
        source = vite._entry_to_ts_path(ENTRY)
        url = vite.vite_asset_url({}, ENTRY)
    assert url == f"http://localhost:5173/@fs{source}"


def test_relative_host_source_keeps_its_existing_dev_route():
    with override_settings(DEBUG=True, VITE_USE_BUILD=False, VITE_HOST_PORT=5173):
        script = str(vite.vite_script("shared/resizer"))
    assert ":5173/static/shared/ts/components/resizer/index.ts" in script
    assert "@fs" not in script
