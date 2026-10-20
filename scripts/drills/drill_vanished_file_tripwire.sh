#!/bin/bash
# Destructive drill, but only inside a disposable clone of the supplied checkout.
set -euo pipefail
EXIT_FILES_MISSING=10
source_checkout="${1:-$(git rev-parse --show-toplevel)}"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
scratch="$tmp/hub-scratch"
git clone --quiet --shared --no-hardlinks "$source_checkout" "$scratch"
candidate="$(git -C "$scratch" ls-files | sed -n '1p')"
if [ -z "$candidate" ] || [ ! -f "$scratch/$candidate" ]; then
    echo "drill refused: no regular tracked-file candidate" >&2
    exit 2
fi
rm -- "$scratch/$candidate"
set +e
bash "$scratch/scripts/utils/detect_vanished_tracked_files.sh" "$scratch" >/dev/null 2>&1
status=$?
set -e
if [ "$status" -ne "$EXIT_FILES_MISSING" ]; then
    echo "drill failed: detector exit=$status expected=$EXIT_FILES_MISSING" >&2
    exit 1
fi
printf '{"event":"scitex_hub.source_dirt.drill","status":"detected","exit_code":%s,"production_mutated":false}\n' "$status"
