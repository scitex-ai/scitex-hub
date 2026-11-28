# OpenID Connect signing key

The hub's OAuth 2 provider (django-oauth-toolkit, mounted at `/oauth/`)
speaks OpenID Connect only when an RSA signing key is configured. With a key:

- `/oauth/.well-known/openid-configuration` serves the discovery document,
- `/oauth/.well-known/jwks.json` serves the public half of the key,
- `openid`-scope logins receive RS256-signed id_tokens.

Without a key, OIDC is off: those two documents are unavailable and
`openid`-scope logins get no id_token.

## Wiring

| Piece | Where |
|---|---|
| Key loader (validates, never logs key material) | `config/settings/settings_auth.py: read_oidc_rsa_private_key` |
| Container path read by Django | `SCITEX_HUB_OIDC_RSA_PRIVATE_KEY_FILE=/run/secrets/scitex-hub-oidc-rsa-key` (set by Compose) |
| Host file mounted there | `SCITEX_HUB_OIDC_RSA_KEY_HOST_FILE` in the deployment's private env file |
| Issuer | derived from `SCITEX_HUB_SITE_URL` + `/oauth` |

An empty or `/dev/null` key file means "no key". A file that exists but is
unreadable or is not an RSA private key stops Django at startup, so a bad
key never ships silently.

## Provisioning a key (per deployment)

1. Generate the key next to the deployment's private env file, never in the
   repository:

   ```bash
   cd deployment/docker/envs
   umask 077
   openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out oidc_rsa_private_key.pem
   ```

   The file must be readable by the user the Django container runs as.
2. Add `SCITEX_HUB_OIDC_RSA_KEY_HOST_FILE=<absolute path of that file>` to the
   private env file.
3. Every OAuth application that requests the `openid` scope must use the
   RS256 algorithm (Django admin, OAuth2 Provider, Applications, "Algorithm").
   An application with no algorithm cannot receive an id_token once OIDC is on.
4. Recreate the Django container so the mount and settings reload, then check:

   ```bash
   curl -s https://<site>/oauth/.well-known/openid-configuration | python -m json.tool
   curl -s https://<site>/oauth/.well-known/jwks.json | python -m json.tool
   ```
