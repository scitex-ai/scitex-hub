"""Field encryption has its own keys, so SECRET_KEY rotation strands nothing.

Covers apps/field_encryption.py, the IntegrationConnection and scholar
UserPreference call sites, and the reencrypt_encrypted_fields command.
"""

from io import StringIO

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps import field_encryption
from apps.infra.integrations_app.models import IntegrationConnection

OLD_SECRET = "old-secret-key-for-tests"  # pragma: allowlist secret
NEW_SECRET = "new-secret-key-for-tests"  # pragma: allowlist secret
K1 = Fernet.generate_key().decode()
K2 = Fernet.generate_key().decode()
ROW = "integrations_app.IntegrationConnection.api_key"

FIELD_KEY = override_settings(
    SECRET_KEY=OLD_SECRET, SECRET_KEY_FALLBACKS=[], FIELD_ENCRYPTION_KEYS=[K1]
)
NO_FIELD_KEY = override_settings(
    SECRET_KEY=OLD_SECRET, SECRET_KEY_FALLBACKS=[], FIELD_ENCRYPTION_KEYS=[]
)
ROTATED = override_settings(
    SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[], FIELD_ENCRYPTION_KEYS=[K1]
)
ROTATED_NO_FIELD_KEY = override_settings(
    SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[], FIELD_ENCRYPTION_KEYS=[]
)
TWO_FIELD_KEYS = override_settings(
    SECRET_KEY=OLD_SECRET, SECRET_KEY_FALLBACKS=[], FIELD_ENCRYPTION_KEYS=[K2, K1]
)


def _legacy_token(secret, value):
    """Ciphertext as the pre-field-key code wrote it: sha256(SECRET_KEY)."""
    return field_encryption._legacy_fernet(secret).encrypt(value.encode()).decode()


def _run(*args):
    out = StringIO()
    call_command("reencrypt_encrypted_fields", *args, stdout=out)
    return out.getvalue()


def _run_expecting_failure(*args):
    """Run the command when it is expected to exit non-zero; swallow that."""
    try:
        _run(*args)
    except CommandError:
        pass


@pytest.fixture
def user(db):
    return User.objects.create_user(username="fieldenc", password="x" * 12)


@pytest.fixture
def legacy_connection(user):
    """A row written by the old code: api_key under sha256(OLD_SECRET)."""
    return IntegrationConnection.objects.create(
        user=user,
        service="anthropic",
        api_key=_legacy_token(OLD_SECRET, "sk-secret-value"),
    )


# -- helper ------------------------------------------------------------------


def test_parse_keys_splits_strips_and_drops_blanks():
    # Arrange
    raw = f" {K1} ,, {K2},"
    # Act
    keys = field_encryption.parse_keys(raw)
    # Assert
    assert keys == [K1, K2]


def test_parse_keys_of_unset_value_is_empty():
    # Arrange
    raw = None
    # Act
    keys = field_encryption.parse_keys(raw)
    # Assert
    assert keys == []


@NO_FIELD_KEY
def test_without_field_key_the_legacy_key_encrypts():
    # Arrange
    legacy = field_encryption._legacy_fernet(OLD_SECRET)
    # Act
    token = field_encryption.encrypt("v")
    # Assert
    assert legacy.decrypt(token.encode()) == b"v"


@FIELD_KEY
def test_with_field_key_the_field_key_encrypts():
    # Arrange
    field_key = Fernet(K1)
    # Act
    token = field_encryption.encrypt("v")
    # Assert
    assert field_key.decrypt(token.encode()) == b"v"


@FIELD_KEY
def test_with_field_key_the_legacy_key_no_longer_encrypts():
    # Arrange
    legacy = field_encryption._legacy_fernet(OLD_SECRET)
    # Act
    token = field_encryption.encrypt("v")
    # Assert
    with pytest.raises(InvalidToken):
        legacy.decrypt(token.encode())


@FIELD_KEY
def test_with_field_key_legacy_ciphertext_still_decrypts():
    # Arrange
    token = _legacy_token(OLD_SECRET, "legacy")
    # Act
    value = field_encryption.decrypt(token)
    # Assert
    assert value == "legacy"


@override_settings(
    SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[OLD_SECRET], FIELD_ENCRYPTION_KEYS=[K1]
)
def test_secret_key_fallbacks_are_accepted_for_legacy_decryption():
    # Arrange
    token = _legacy_token(OLD_SECRET, "x")
    # Act
    value = field_encryption.decrypt(token)
    # Assert
    assert value == "x"


def test_field_key_ciphertext_survives_secret_key_rotation():
    # Arrange
    with FIELD_KEY:
        token = field_encryption.encrypt("survives")
    # Act
    with ROTATED:
        value = field_encryption.decrypt(token)
    # Assert
    assert value == "survives"


@TWO_FIELD_KEYS
def test_key_state_newest_key_is_current():
    # Arrange
    token = Fernet(K2).encrypt(b"a").decode()
    # Act
    state = field_encryption.key_state(token)
    # Assert
    assert state == field_encryption.CURRENT


@TWO_FIELD_KEYS
def test_key_state_older_field_key_is_stale():
    # Arrange
    token = Fernet(K1).encrypt(b"b").decode()
    # Act
    state = field_encryption.key_state(token)
    # Assert
    assert state == field_encryption.STALE


@TWO_FIELD_KEYS
def test_key_state_legacy_key_is_stale():
    # Arrange
    token = _legacy_token(OLD_SECRET, "c")
    # Act
    state = field_encryption.key_state(token)
    # Assert
    assert state == field_encryption.STALE


@TWO_FIELD_KEYS
def test_key_state_foreign_key_is_unreadable():
    # Arrange
    token = Fernet(Fernet.generate_key()).encrypt(b"d").decode()
    # Act
    state = field_encryption.key_state(token)
    # Assert
    assert state == field_encryption.UNREADABLE


@TWO_FIELD_KEYS
def test_reencrypt_moves_value_to_newest_key():
    # Arrange
    token = Fernet(K1).encrypt(b"b").decode()
    # Act
    rotated = field_encryption.reencrypt(token)
    # Assert
    assert Fernet(K2).decrypt(rotated.encode()) == b"b"


@override_settings(FIELD_ENCRYPTION_KEYS=["not-a-fernet-key"])
def test_invalid_key_fails_loudly_without_echoing_it():
    # Arrange
    expected = rf"^{field_encryption.ENV_NAME} entry 0 is not a valid Fernet key$"
    # Act
    call = lambda: field_encryption.encrypt("v")  # noqa: E731
    # Assert
    with pytest.raises(ImproperlyConfigured, match=expected):
        call()


def test_empty_value_encrypts_to_empty():
    # Arrange
    value = ""
    # Act
    token = field_encryption.encrypt(value)
    # Assert
    assert token == ""


# -- models ------------------------------------------------------------------


@FIELD_KEY
def test_integration_connection_api_key_round_trips(user):
    # Arrange
    conn = IntegrationConnection(user=user, service="anthropic")
    conn.set_api_key("sk-test")
    conn.save()
    # Act
    conn.refresh_from_db()
    # Assert
    assert conn.get_api_key() == "sk-test"


@FIELD_KEY
def test_integration_connection_stores_ciphertext_not_plaintext(user):
    # Arrange
    conn = IntegrationConnection(user=user, service="anthropic")
    # Act
    conn.set_api_key("sk-test")
    # Assert
    assert "sk-test" not in conn.api_key


@ROTATED_NO_FIELD_KEY
def test_unreadable_secret_reads_as_not_set_instead_of_raising(legacy_connection):
    # Arrange
    conn = legacy_connection
    # Act
    value = conn.get_api_key()
    # Assert
    assert value == ""


@FIELD_KEY
def test_scholar_preference_api_key_round_trips(user):
    """Regression: this used to read the undefined setting
    SCITEX_HUB_DJANGO_SECRET_KEY and raise AttributeError on every save."""
    # Arrange
    from apps.workspace.scholar_app.models import UserPreference

    pref = UserPreference.objects.create(user=user)
    # Act
    pref.set_api_key("pubmed", "ncbi-key")
    # Assert
    assert UserPreference.objects.get(pk=pref.pk).get_api_key("pubmed") == "ncbi-key"


# -- command -----------------------------------------------------------------


@NO_FIELD_KEY
def test_command_refuses_without_a_field_key(db):
    # Arrange
    args = ()
    # Act
    call = lambda: _run(*args)  # noqa: E731
    # Assert
    with pytest.raises(CommandError, match=field_encryption.ENV_NAME):
        call()


@FIELD_KEY
def test_command_check_fails_while_values_are_stale(legacy_connection):
    # Arrange
    args = ("--check",)
    # Act
    call = lambda: _run(*args)  # noqa: E731
    # Assert
    with pytest.raises(CommandError, match="need re-encryption"):
        call()


@FIELD_KEY
def test_command_check_writes_nothing(legacy_connection):
    # Arrange
    before = legacy_connection.api_key
    # Act
    _run_expecting_failure("--check")
    # Assert
    assert IntegrationConnection.objects.get(pk=legacy_connection.pk).api_key == before


@FIELD_KEY
def test_command_reencrypts_stale_values(legacy_connection):
    # Arrange
    expected = f"{ROW}: current=0 reencrypted=1 stale=0 unreadable=0"
    # Act
    output = _run()
    # Assert
    assert expected in output


@FIELD_KEY
def test_command_second_run_is_a_no_op(legacy_connection):
    # Arrange
    _run()
    # Act
    output = _run()
    # Assert
    assert f"{ROW}: current=1 reencrypted=0 stale=0 unreadable=0" in output


@FIELD_KEY
def test_command_check_passes_once_everything_is_current(legacy_connection):
    # Arrange
    _run()
    # Act
    output = _run("--check")
    # Assert
    assert "TOTAL: current=1 reencrypted=0 stale=0 unreadable=0" in output


@FIELD_KEY
def test_command_never_prints_values_or_keys(legacy_connection):
    # Arrange
    secrets = ("sk-secret-value", K1, legacy_connection.api_key)
    # Act
    output = _run() + _run()
    # Assert
    assert not [s for s in secrets if s in output]


@FIELD_KEY
def test_command_does_not_bump_updated_at(legacy_connection):
    # Arrange
    before = IntegrationConnection.objects.get(pk=legacy_connection.pk).updated_at
    # Act
    _run()
    # Assert
    assert (
        IntegrationConnection.objects.get(pk=legacy_connection.pk).updated_at == before
    )


def test_reencrypted_value_survives_secret_key_rotation(legacy_connection):
    # Arrange
    with FIELD_KEY:
        _run()
    # Act
    with ROTATED:
        value = IntegrationConnection.objects.get(pk=legacy_connection.pk).get_api_key()
    # Assert
    assert value == "sk-secret-value"


@ROTATED
def test_command_fails_on_unreadable_values(legacy_connection):
    # Arrange
    args = ()
    # Act
    call = lambda: _run(*args)  # noqa: E731
    # Assert
    with pytest.raises(CommandError, match="unreadable"):
        call()


@ROTATED
def test_command_leaves_unreadable_values_untouched(legacy_connection):
    # Arrange
    before = legacy_connection.api_key
    # Act
    _run_expecting_failure()
    # Assert
    assert IntegrationConnection.objects.get(pk=legacy_connection.pk).api_key == before
