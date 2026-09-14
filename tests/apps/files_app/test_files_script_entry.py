"""The Files page script is a platform Vite entry, not a dev-installed app."""

from apps.infra.public_app.templatetags.vite import _is_dev_app_entry


def test_files_script_is_served_as_a_platform_entry():
    # Arrange
    entry = "files_app/files"
    # Act
    is_dev_app = _is_dev_app_entry(entry)
    # Assert
    assert is_dev_app is False
