# Production baked frontend

The production Dockerfile selects `SCITEX_HUB_FRONTEND_MODE=baked` together with
`SCITEX_APPS_PYTHON_MODE=image-only`. Build and qualify one image, then stage and
promote that exact image identity. Do not rebuild between staging and production.

After the normal full Python dependency installation, Docker runs:

```bash
python scripts/deploy/bake_frontend.py --app-root /app --artifact /opt/scitex-frontend
```

The frontend-only installer reads the existing six-app registry. Each installed
release must have a matching public `v<version>` Git tag, exact resolved commit,
clean checkout, and matching source project name/version. Mutable `develop` refs
are not used. Existing source directories and editable distribution inputs are
refused. Checkouts are siblings of `/app` (`/scitex-ui`, `/figrecipe`, etc.), so
legacy root `file:../...` inputs have an admitted build layout. Existing local
npm dependency declarations are rebound only to verified providers of the same
npm package name; the receipt records the original and resolved declarations.
SDK and Live Paper npm providers come from their installed wheel namespaces.
The SDK namespace must match the exact-version public PyPI wheel byte for byte.

The installer creates lockfiles from these pinned local providers and runs normal
`npm ci` for every declared root/bridge frontend package, followed by the full Hub
`npm run build`. No Python reinstall, reduced npm install, ignored frontend error,
or editable fallback is used. A missing public tag, provider, lock closure, or
build prerequisite fails the image build. The pre/post Python version graph must
be identical. Public tags are resolved at build time and their immutable commits
and trees are recorded; the same-image promotion rule prevents later retagging
from changing a staged frontend.

`/opt/scitex-frontend/receipt.json` records frontend source/lock hashes, public SDK
wheel identity and namespace hashes, all installed Python versions, source tag
commits/trees, and every generated Vite member. The artifact and the standalone
verification tool under `/opt/scitex-frontend-tools` are root-owned and not
writable by the application user. The receipt describes frontend inputs, not a
claim that every Hub source file was hashed. Preserve the image's source identity
and the normal dependency/source qualification separately.

Startup still checks dependencies, waits for the database, applies required
migrations, and runs collectstatic. The web role then verifies the protected
artifact, current source/locks, complete Vite manifest closure, SDK namespace,
and installed version graph. It copies the verified closure into the existing
`/app/staticfiles/vite` volume and publishes the manifest last. Older hashed
chunks remain available. Publication is atomic per file, not a transaction over
the entire directory. Verification or copying failure stops startup; baked mode
never falls back to Git/npm. Worker and beat retain their existing role behavior.

An unknown frontend mode, or baked mode with editable Python mode, is refused.
The canonical Compose resolver sets both modes together: production and explicit
staging candidate images use `image-only`/`baked`; ordinary staging uses
`editable`/`build`, explicitly overriding the production image defaults. Ambient
mode variables cannot change that derived policy. Development rejects candidate
image overrides and keeps its own startup path. Changing modes is not a migration
bypass.

Before promotion, qualify a real cold Docker build, its receipt and actual route
assets on an isolated staging database/users root. Unit protocol fixtures alone
do not establish a successful production frontend build. Keep old image and
static backups; image rollback does not undo database migrations. New publication
retains previous hashed chunks but does not restore overwritten nonhashed files.
