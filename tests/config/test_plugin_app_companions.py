"""Published FigRecipe companion declarations survive actual Django admission."""

from django.apps.registry import Apps
from scitex_sdk.app.plugins import PluginApp

from config.settings._optional_apps import _with_host_plugin_apps, with_plugin_apps

PRIMARY = "figrecipe._django.apps.FigRecipeEditorConfig"
COMPANION = "figrecipe._django.apps.ScitexAppChatConfig"


def _identities(entries):
    return [
        (cfg.name, cfg.label) for cfg in Apps(installed_apps=entries).get_app_configs()
    ]


def test_published_companion_is_retained_and_populates_the_real_registry():
    # Arrange
    plugin = PluginApp("figrecipe", PRIMARY)
    # Act
    merged = with_plugin_apps(["figrecipe._django"], [plugin])
    observed = _identities(merged)
    # Assert: metadata alone cannot prove Django can populate both owners.
    assert (merged, observed) == (
        [PRIMARY, COMPANION],
        [
            ("figrecipe._django", "figrecipe_editor"),
            ("scitex_sdk.app._chat", "scitex_app"),
        ],
    )


def test_already_present_companion_is_not_added_a_second_time():
    # Arrange
    plugin = PluginApp("figrecipe", PRIMARY)
    # Act
    merged = with_plugin_apps(["figrecipe._django", COMPANION], [plugin])
    observed = _identities(merged)
    # Assert
    assert (merged, observed) == (
        [PRIMARY, COMPANION],
        [
            ("figrecipe._django", "figrecipe_editor"),
            ("scitex_sdk.app._chat", "scitex_app"),
        ],
    )


def test_companion_already_owned_by_the_host_keeps_one_registration():
    # Arrange
    plugin = PluginApp("figrecipe", PRIMARY)
    # Act
    merged = _with_host_plugin_apps(["figrecipe._django"], [COMPANION], [plugin])
    observed = _identities([COMPANION, *merged])
    # Assert
    assert (merged, observed) == (
        [PRIMARY],
        [
            ("scitex_sdk.app._chat", "scitex_app"),
            ("figrecipe._django", "figrecipe_editor"),
        ],
    )
