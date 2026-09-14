"""Dev settings must work behind PgBouncer in transaction pooling mode.

The dev hub database moves onto the scitex store server, reached through
PgBouncer (transaction mode). Server-side cursors break there, as they would
in production, so dev disables them the same way settings_prod does.
"""

from django.conf import settings


def test_dev_settings_disable_server_side_cursors_for_pgbouncer():
    # Arrange
    database = settings.DATABASES["default"]

    # Act
    disabled = database.get("DISABLE_SERVER_SIDE_CURSORS", False)

    # Assert
    assert disabled is True
