#!/usr/bin/env bash
# Deploy the status.scitex.ai Worker. Idempotent; safe to re-run.
#
#   ./deploy.sh          dry run — shows what would happen
#   ./deploy.sh --apply  upload the script and ensure the route exists
#
# Credentials are sourced from the operator's shell secret files and are never
# echoed. Nothing here writes to the tunnel or to DNS.
set -uo pipefail
MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# The secret files live in the OPERATOR's home. An agent container runs as a
# different user ($HOME=/home/agent) while bind-mounting the operator's home, so
# $HOME alone finds nothing and the deploy dead-ends on "api key not loaded" even
# though the files are right there and readable. SCITEX_SECRETS_HOME lets the
# caller say where they are without editing this script or faking $HOME for the
# whole process.
SECRETS_HOME="${SCITEX_SECRETS_HOME:-$HOME}"
# shellcheck disable=SC1091
source "$SECRETS_HOME/.bash.d/secrets/000_ENV/api_keys/50_scitex_cloudflare.src" 2>/dev/null
# shellcheck disable=SC1091
source "$SECRETS_HOME/.bash.d/secrets/010_scitex/99_cloudflare.src" 2>/dev/null

# Credentials are required only to UPLOAD. The dry run prints the plan and runs
# the renderer self-check, neither of which touches Cloudflare — so demanding a
# key up front made `./deploy.sh` unusable anywhere the secrets are not mounted
# (an agent container, CI), for a run that could never have called the API.
# Checked at the point of use instead.
if [ "$MODE" = "--apply" ]; then
  : "${SCITEX_CLOUDFLARE_EMAIL:?cloudflare email not loaded from $SECRETS_HOME/.bash.d/secrets/010_scitex/99_cloudflare.src — if the operator home is elsewhere, set SCITEX_SECRETS_HOME=/home/<operator>}"
  : "${SCITEX_CLOUDFLARE_API_KEY:?cloudflare api key not loaded from $SECRETS_HOME/.bash.d/secrets/000_ENV/api_keys/50_scitex_cloudflare.src — if the operator home is elsewhere, set SCITEX_SECRETS_HOME=/home/<operator>}"
fi

ACCOUNT_ID=d76d6c5622f131502fb01672fc5a9bb3
ZONE_ID=d075a7ed6e3b3b00ec931124c4b09509
SCRIPT_NAME=scitex-status
ROUTE_PATTERN='status.scitex.ai/*'
API=https://api.cloudflare.com/client/v4
AUTH=(-H "X-Auth-Email: ${SCITEX_CLOUDFLARE_EMAIL:-}" -H "X-Auth-Key: ${SCITEX_CLOUDFLARE_API_KEY:-}")

echo "script : $SCRIPT_NAME"
echo "route  : $ROUTE_PATTERN"
echo "source : $HERE/worker.js ($(wc -c < "$HERE/worker.js") bytes)"
echo "         $HERE/internals.js ($(wc -c < "$HERE/internals.js") bytes)"

# A GATE THAT CANNOT FAIL IS NOT A GATE. This one can: it renders a fixture
# shaped like the real /api/status/ payload and fails the deploy if any section
# vanishes, if a value stops appearing, or if HTML in a value is not escaped.
# A status page that renders blank looks exactly like "nothing to report", so
# this must run BEFORE the upload, not after.
echo
echo "self-check..."
if ! node "$HERE/selftest.mjs" > /tmp/status-worker-selftest.$$ 2>&1; then
  tail -30 /tmp/status-worker-selftest.$$
  rm -f /tmp/status-worker-selftest.$$
  echo
  echo "ABORT: renderer self-check FAILED — nothing uploaded."
  echo "Fix internals.js (or update the fixture in selftest.mjs if a hub check"
  echo "renamed a field), then re-run. Full output: node $HERE/selftest.mjs"
  exit 1
fi
echo "self-check passed ($(grep -c '^ok ' /tmp/status-worker-selftest.$$) checks)"
rm -f /tmp/status-worker-selftest.$$

if [ "$MODE" != "--apply" ]; then
  echo
  echo "DRY RUN — nothing uploaded. Re-run with --apply."
  exit 0
fi

TMP_META="$(mktemp)"
trap 'rm -f "$TMP_META"' EXIT
printf '{"main_module":"worker.js","compatibility_date":"2025-01-01"}' > "$TMP_META"

echo
echo "uploading..."
# NOTE: ;filename=<name> is REQUIRED on EVERY part. Cloudflare resolves modules by
# the part's filename, not the form field name; without it the upload fails with
# "No such module: worker.js". The same applies to each additional module —
# worker.js imports "./internals.js", which resolves against these filenames.
# Multiple parts is NOT a build step: no bundler, no dependencies, one PUT.
curl -sS --max-time 60 "${AUTH[@]}" -X PUT \
  "$API/accounts/$ACCOUNT_ID/workers/scripts/$SCRIPT_NAME" \
  -F "metadata=@$TMP_META;type=application/json" \
  -F "worker.js=@$HERE/worker.js;filename=worker.js;type=application/javascript+module" \
  -F "internals.js=@$HERE/internals.js;filename=internals.js;type=application/javascript+module" \
 | python3 -c 'import sys,json;d=json.load(sys.stdin);print("upload success=",d.get("success"));print("errors=",d.get("errors"))'

echo
echo "ensuring route..."
existing=$(curl -sS --max-time 30 "${AUTH[@]}" "$API/zones/$ZONE_ID/workers/routes" \
  | python3 -c 'import sys,json;print(any(r.get("pattern")=="'"$ROUTE_PATTERN"'" for r in (json.load(sys.stdin).get("result") or [])))')
if [ "$existing" = "True" ]; then
  echo "route already present — nothing to do"
else
  curl -sS --max-time 30 "${AUTH[@]}" -H "Content-Type: application/json" -X POST \
    "$API/zones/$ZONE_ID/workers/routes" \
    --data "{\"pattern\":\"$ROUTE_PATTERN\",\"script\":\"$SCRIPT_NAME\"}" \
   | python3 -c 'import sys,json;d=json.load(sys.stdin);print("route success=",d.get("success"));print("errors=",d.get("errors"))'
fi

echo
echo "verifying..."
# upstream_available is the half that used to be missing: it reports whether the
# hub's own /api/status/ answered, i.e. whether Internal metrics can render at
# all. It is printed explicitly so a deploy that leaves the page half-blind is
# visible here rather than discovered on the page.
curl -sS --max-time 30 https://status.scitex.ai/api/status \
 | python3 -c 'import sys,json
d=json.load(sys.stdin)
print("ok=", d.get("ok"))
print("upstream_available=", d.get("upstream_available"))
u=d.get("upstream") or {}
print("upstream_schema=", u.get("schema"))
print("upstream_complete=", u.get("complete"))
for s in d.get("services", []):
    print(" ", s["name"], s["up"], s["status"])'
