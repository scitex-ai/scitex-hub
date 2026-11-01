"""Legacy CSS imports follow the actual SDK export while JS stays compatible."""

import json
import re
from pathlib import Path

import scitex_sdk

ROOT = Path(__file__).resolve().parents[2]


def test_css_aliases_precede_the_broad_legacy_prefix_and_use_sdk_exports():
    # Arrange
    config = (ROOT / "vite.config.ts").read_text()
    # Act
    css_alias = config.index('"scitex-ui/css": SCITEX_SDK_CSS')
    broad_alias = config.index('"scitex-ui": SCITEX_UI_STATIC')
    # Assert
    assert (
        css_alias < broad_alias
        and 'scitexSdkSubpathAliases()["@scitex/sdk/ui/css"]' in config
    )


def test_collectstatic_css_spelling_uses_the_same_sdk_owner():
    # Arrange
    config = (ROOT / "vite.config.ts").read_text()
    # Act
    primary_css_aliases = re.findall(
        r'"(scitex-ui/css|\.\./\.\./\.\./scitex_ui/css)": SCITEX_SDK_CSS', config
    )
    # Assert
    assert set(primary_css_aliases) == {"scitex-ui/css", "../../../scitex_ui/css"}


def test_canonical_export_points_to_the_actual_shipped_css_directory():
    # Arrange
    sdk = Path(scitex_sdk.__file__).resolve().parent
    exports = json.loads((sdk / "package.json").read_text())["exports"]
    # Act
    target = sdk / exports["./ui/css/*"].removesuffix("*")
    # Assert
    assert (target / "shell/stx-shell-sidebar.css").is_file() and (
        target / "shell/app-shell.css"
    ).is_file()


def test_existing_legacy_javascript_aliases_are_preserved():
    # Arrange
    config = (ROOT / "vite.config.ts").read_text()
    # Act
    unchanged = (
        '"scitex-ui": SCITEX_UI_STATIC' in config
        and '"@scitex/ui": resolve(SCITEX_UI_STATIC, "../../../..")' in config
    )
    # Assert
    assert unchanged
