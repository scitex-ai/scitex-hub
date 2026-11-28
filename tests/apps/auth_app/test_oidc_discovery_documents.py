#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAuth / OpenID Connect discovery documents are served when a key is configured.

OAuth and MCP clients discover the hub's endpoints from
``/oauth/.well-known/openid-configuration`` and verify id_tokens against
``/oauth/.well-known/jwks.json``. Both come from django-oauth-toolkit and
exist only while OIDC is enabled, which the settings tie to a configured RSA
signing key (``config.settings.settings_auth.read_oidc_rsa_private_key``).
"""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from django.core.exceptions import ImproperlyConfigured

from config.settings.settings_auth import read_oidc_rsa_private_key

DISCOVERY = "/oauth/.well-known/openid-configuration"
JWKS = "/oauth/.well-known/jwks.json"
DISCOVERY_FIELDS = [
    "issuer",
    "authorization_endpoint",
    "token_endpoint",
    "userinfo_endpoint",
    "jwks_uri",
    "response_types_supported",
    "subject_types_supported",
    "id_token_signing_alg_values_supported",
    "scopes_supported",
]


def _pem(private_key) -> str:
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture(scope="module")
def rsa_pem() -> str:
    return _pem(rsa.generate_private_key(public_exponent=65537, key_size=2048))


@pytest.fixture
def oidc_on(settings, rsa_pem):
    settings.OAUTH2_PROVIDER = {
        **settings.OAUTH2_PROVIDER,
        "OIDC_ENABLED": True,
        "OIDC_RSA_PRIVATE_KEY": rsa_pem,
    }


@pytest.fixture
def discovery(client, oidc_on):
    return client.get(DISCOVERY)


@pytest.fixture
def jwks(client, oidc_on):
    return client.get(JWKS)


@pytest.mark.django_db
class TestOpenIdConfiguration:
    def test_discovery_document_returns_200(self, discovery):
        # Arrange
        response = discovery
        # Act
        status = response.status_code
        # Assert
        assert status == 200

    def test_discovery_document_is_served_as_json(self, discovery):
        # Arrange
        response = discovery
        # Act
        content_type = response["Content-Type"]
        # Assert
        assert content_type.startswith("application/json")

    @pytest.mark.parametrize("field", DISCOVERY_FIELDS)
    def test_discovery_document_has_required_field(self, discovery, field):
        # Arrange
        document = json.loads(discovery.content)
        # Act
        present = field in document
        # Assert
        assert present

    def test_advertises_rs256_signing(self, discovery):
        # Arrange
        document = json.loads(discovery.content)
        # Act
        algorithms = document["id_token_signing_alg_values_supported"]
        # Assert
        assert "RS256" in algorithms

    def test_points_at_the_jwks_document(self, discovery):
        # Arrange
        document = json.loads(discovery.content)
        # Act
        jwks_uri = document["jwks_uri"]
        # Assert
        assert jwks_uri.endswith(JWKS)


@pytest.mark.django_db
class TestJwks:
    def test_jwks_document_returns_200(self, jwks):
        # Arrange
        response = jwks
        # Act
        status = response.status_code
        # Assert
        assert status == 200

    def test_jwks_document_is_served_as_json(self, jwks):
        # Arrange
        response = jwks
        # Act
        content_type = response["Content-Type"]
        # Assert
        assert content_type.startswith("application/json")

    @pytest.mark.parametrize(
        "field,expected", [("kty", "RSA"), ("alg", "RS256"), ("use", "sig")]
    )
    def test_jwks_key_declares_rsa_signing_field(self, jwks, field, expected):
        # Arrange
        key = json.loads(jwks.content)["keys"][0]
        # Act
        value = key.get(field)
        # Assert
        assert value == expected

    @pytest.mark.parametrize("field", ["kid", "n", "e"])
    def test_key_has_public_parameter(self, jwks, field):
        # Arrange
        key = json.loads(jwks.content)["keys"][0]
        # Act
        present = bool(key.get(field))
        # Assert
        assert present

    @pytest.mark.parametrize("field", ["d", "p", "q", "dp", "dq", "qi"])
    def test_never_publishes_private_parameters(self, jwks, field):
        # Arrange
        key = json.loads(jwks.content)["keys"][0]
        # Act
        present = field in key
        # Assert
        assert not present


class TestSigningKeyLoader:
    def test_unset_means_no_key(self):
        # Arrange
        environ = {}
        # Act
        pem = read_oidc_rsa_private_key(environ)
        # Assert
        assert pem == ""

    def test_empty_file_means_no_key(self, tmp_path):
        # Arrange
        empty = tmp_path / "empty.pem"
        empty.write_text("")
        # Act
        pem = read_oidc_rsa_private_key(
            {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(empty)}
        )
        # Assert
        assert pem == ""

    def test_rsa_key_file_is_loaded(self, tmp_path, rsa_pem):
        # Arrange
        key_file = tmp_path / "key.pem"
        key_file.write_text(rsa_pem)
        # Act
        pem = read_oidc_rsa_private_key(
            {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(key_file)}
        )
        # Assert
        assert pem == rsa_pem.strip()

    def test_missing_file_fails_loudly(self, tmp_path):
        # Arrange
        environ = {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(tmp_path / "nope.pem")}
        # Act
        load = lambda: read_oidc_rsa_private_key(environ)  # noqa: E731
        # Assert
        with pytest.raises(ImproperlyConfigured):
            load()

    def test_garbage_file_fails_loudly(self, tmp_path):
        # Arrange
        garbage = tmp_path / "garbage.pem"
        garbage.write_text("not a key")
        environ = {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(garbage)}
        # Act
        load = lambda: read_oidc_rsa_private_key(environ)  # noqa: E731
        # Assert
        with pytest.raises(ImproperlyConfigured):
            load()

    def test_non_rsa_key_fails_loudly(self, tmp_path):
        # Arrange
        ec_file = tmp_path / "ec.pem"
        ec_file.write_text(_pem(ec.generate_private_key(ec.SECP256R1())))
        environ = {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(ec_file)}
        # Act
        load = lambda: read_oidc_rsa_private_key(environ)  # noqa: E731
        # Assert
        with pytest.raises(ImproperlyConfigured):
            load()

    def test_error_never_contains_key_material(self, tmp_path):
        # Arrange
        garbage = tmp_path / "garbage.pem"
        garbage.write_text("SENTINEL-KEY-MATERIAL")
        environ = {"SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE": str(garbage)}
        # Act
        try:
            read_oidc_rsa_private_key(environ)
            message = ""
        except ImproperlyConfigured as error:
            message = str(error)
        # Assert
        assert "SENTINEL" not in message
