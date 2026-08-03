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

# shellcheck disable=SC1091
source "$HOME/.bash.d/secrets/000_ENV/api_keys/50_scitex_cloudflare.src" 2>/dev/null
# shellcheck disable=SC1091
source "$HOME/.bash.d/secrets/010_scitex/99_cloudflare.src" 2>/dev/null
: "${SCITEX_CLOUDFLARE_EMAIL:?cloudflare email not loaded}"
: "${SCITEX_CLOUDFLARE_API_KEY:?cloudflare api key not loaded}"

ACCOUNT_ID=d76d6c5622f131502fb01672fc5a9bb3
ZONE_ID=d075a7ed6e3b3b00ec931124c4b09509
SCRIPT_NAME=scitex-status
ROUTE_PATTERN='status.scitex.ai/*'
API=https://api.cloudflare.com/client/v4
AUTH=(-H "X-Auth-Email: $SCITEX_CLOUDFLARE_EMAIL" -H "X-Auth-Key: $SCITEX_CLOUDFLARE_API_KEY")

echo "script : $SCRIPT_NAME"
echo "route  : $ROUTE_PATTERN"
echo "source : $HERE/worker.js ($(wc -c < "$HERE/worker.js") bytes)"

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
# NOTE: ;filename=worker.js is REQUIRED. Cloudflare resolves the module by the
# part's filename, not the form field name; without it the upload fails with
# "No such module: worker.js".
curl -sS --max-time 60 "${AUTH[@]}" -X PUT \
  "$API/accounts/$ACCOUNT_ID/workers/scripts/$SCRIPT_NAME" \
  -F "metadata=@$TMP_META;type=application/json" \
  -F "worker.js=@$HERE/worker.js;filename=worker.js;type=application/javascript+module" \
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
curl -sS --max-time 30 https://status.scitex.ai/api/status \
 | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok=",d.get("ok"));[print(" ",s["name"],s["up"],s["status"]) for s in d.get("services",[])]'
